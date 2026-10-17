import argparse
import gzip
import hashlib
import html
import json
import re
from pathlib import Path

import pandas as pd

CARDS_DIR = Path("data/raw/cdtrf/cards")
OUT_PATH = Path("data/interim/cdtrf_cards.parquet")

NUXT_RE = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
VIN_RE = re.compile(r"(?<![A-Za-z0-9А-Яа-я])(?:VIN[\s:-]*)?([A-HJ-NPR-Z0-9АВЕКМНОРСТХ]{17})(?![A-Za-z0-9А-Яа-я])", re.I)
MIN_VIN_DIGITS = 3
APARTMENT_RE = re.compile(r"\b(кв\.?|квартира)\s*№?\s*\d+\w*", re.I)
PHONE_RE = re.compile(r"(?:\+7|\b8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b")
CYR_TO_LAT = str.maketrans("АВЕКМНОРСТХ", "ABEKMHOPCTX")
PLATE_RE = re.compile(r"\b[АВЕКМНОРСТУХABEKMHOPCTYX]\s?\d{3}\s?[АВЕКМНОРСТУХABEKMHOPCTYX0]{2}\s?/?\s?\d{2,3}\b", re.I)
INN_RE = re.compile(r"(ИНН[\s:№]*)\d{10,12}\b|(?<!\d)\d{12}(?!\d)", re.I)
SNILS_RE = re.compile(r"\b\d{3}-\d{3}-\d{3}[\s-]?\d{2}\b")
NAME_RE = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}(?:вич|вн|чн|оглы|угли|кызы)[а-яё]*\b|\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.")
WRAPPERS = {"ShallowReactive", "Reactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef", "NuxtError"}

TRADE_FIELDS = [
    "tradeId", "idEFRSB", "tradeType", "tradeTypeDescription", "tradeStatus", "tradeForm", "priceType",
    "debtType", "dateInEFRSB", "declarateTime", "requestTimeBegin", "requestTimeEnd", "auctionTimeBegin",
    "winnerTime", "salesContractTime", "salesContractType", "winnerPriceOffer", "allPartReqCount",
]
LOT_FIELDS = ["tradeLotId", "lotNumber", "priceBegin", "decreaseRules", "regionID", "categoryIDs"]
DATE_FORMATS = {
    "dateInEFRSB": "%d.%m.%Y",
    "declarateTime": "%d.%m.%Y %H:%M:%S",
    "requestTimeBegin": "%d.%m.%Y %H:%M",
    "requestTimeEnd": "%d.%m.%Y %H:%M",
    "auctionTimeBegin": "%d.%m.%Y %H:%M",
    "winnerTime": "%d.%m.%Y %H:%M",
    "salesContractTime": "%d.%m.%Y",
}


def decode_devalue(payload: list):
    cache = {}

    def resolve(index):
        if not isinstance(index, int):
            return index
        if index < 0:
            return None
        if index in cache:
            return cache[index]
        value = payload[index]
        if isinstance(value, list):
            tag = value[0] if value else None
            if isinstance(tag, str) and tag in WRAPPERS:
                result = resolve(value[1]) if len(value) > 1 else None
            elif tag == "Date":
                result = value[1]
            elif tag == "Set":
                result = [resolve(i) for i in value[1:]]
            elif tag in ("Map", "null"):
                result = {str(resolve(k)): resolve(v) for k, v in zip(value[1::2], value[2::2])}
            else:
                result = [resolve(i) for i in value]
        elif isinstance(value, dict):
            result = {}
            cache[index] = result
            for key, i in value.items():
                result[key] = resolve(i)
        else:
            result = value
        cache[index] = result
        return result

    return resolve(0)


def to_number(value) -> float | None:
    if value in (None, ""):
        return None
    return float(str(value).replace("\xa0", "").replace(" ", "").replace(",", "."))


def _is_vin(candidate: str) -> bool:
    return sum(ch.isdigit() for ch in candidate) >= MIN_VIN_DIGITS


def find_vins(text: str | None) -> list[str]:
    return [v.upper().translate(CYR_TO_LAT) for v in VIN_RE.findall(text or "") if _is_vin(v)]


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = html.unescape(TAG_RE.sub(" ", value))
    text = VIN_RE.sub(lambda m: "[VIN]" if _is_vin(m.group(1)) else m.group(0), text)
    text = PLATE_RE.sub("[НОМЕР]", text)
    text = PHONE_RE.sub("[ТЕЛЕФОН]", text)
    text = SNILS_RE.sub("[СНИЛС]", text)
    text = INN_RE.sub(lambda m: f"{m.group(1) or ''}[ИНН]", text)
    text = NAME_RE.sub("[ФИО]", text)
    text = APARTMENT_RE.sub(lambda m: f"{m.group(1)} [НОМЕР]", text)
    return re.sub(r"\s+", " ", text).strip()


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def debtor_key(trade: dict) -> str | None:
    inn = trade.get("debtNatINN") or trade.get("debtJurINN")
    return short_hash(inn) if inn else None


def debtor_name_key(record: dict) -> str | None:
    parts = [record.get(k) or "" for k in ("debtLastName", "debtFirstName", "debtMiddleName", "debtShortName")]
    name = " ".join(" ".join(parts).lower().replace("ё", "е").split())
    return short_hash(name) if name else None


def title_key(title: str | None) -> str | None:
    text = re.sub(r"[^0-9a-zа-я]", "", (title or "").lower().replace("ё", "е"))
    return short_hash(text) if text else None


def parse_card(path: Path) -> dict | None:
    return parse_html(gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text())


def parse_html(raw: str) -> dict | None:
    match = NUXT_RE.search(raw)
    if not match:
        return None
    root = decode_devalue(json.loads(match.group(1)))
    trade = next(iter(root["data"].values()))
    lot = trade["lot"]

    vins = find_vins(lot.get("lotInfo"))
    row = {key: trade.get(key) for key in TRADE_FIELDS}
    row.update({f"lot_{key}": lot.get(key) for key in LOT_FIELDS})
    row["lot_info"] = clean_text(lot.get("lotInfo"))
    row["lot_title"] = clean_text(lot.get("name"))
    row["lot_decreaseRules"] = clean_text(lot.get("decreaseRules"))
    row["lot_priceBegin"] = to_number(lot.get("priceBegin"))
    row["winnerPriceOffer"] = to_number(trade.get("winnerPriceOffer"))
    sole_participant = "единственным участником" in (trade.get("salesContractType") or "")
    row["sale_price"] = row["winnerPriceOffer"] or (row["lot_priceBegin"] if sole_participant else None)
    row["n_schedule_periods"] = len(lot.get("lotScheduleItems") or [])
    row["n_vins"] = len(set(vins))
    row["vin_wmi"] = vins[0][:3] if vins else None
    row["vin_vds"] = vins[0][3:8] if vins else None
    row["vin_year_code"] = vins[0][9] if vins else None
    row["vin_hash"] = short_hash(vins[0]) if vins else None
    row["debtor_key"] = debtor_key(trade)
    row["debtor_name_key"] = debtor_name_key(trade)
    row["title_key"] = title_key(row["lot_title"])
    court = re.match(r"\s*[АA](\d{2,3})", trade.get("dealNum") or "")
    row["court_code"] = court.group(1) if court else None
    row["n_images"] = len(lot.get("images") or [])
    inn = trade.get("arbManINN")
    row["arbman_key"] = short_hash(inn) if inn else None
    row["arbman_sro"] = str(trade["arbManOrgId"]) if trade.get("arbManOrgId") is not None else None
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards-dir", type=Path, default=CARDS_DIR)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    paths = sorted([*args.cards_dir.glob("*.html"), *args.cards_dir.glob("*.html.gz")])
    rows = [parse_card(path) for path in paths]
    df = pd.DataFrame([row for row in rows if row])
    for column, fmt in DATE_FORMATS.items():
        df[column] = pd.to_datetime(df[column], format=fmt)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    print(f"{len(df)} cards -> {args.out}, not parsed: {len(rows) - len(df)}")


if __name__ == "__main__":
    main()
