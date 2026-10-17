from pathlib import Path

import numpy as np
import pandas as pd

from src.dataset.stages import TRADES_PATH, add_first_price
from src.features.normalize import normalize_models
from src.features.text import extract_frame

CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")
OUT_PATH = Path("data/processed/lots.parquet")
SINCE = pd.Timestamp("2023-01-01")
TEST_START = pd.Timestamp("2026-01-01")
COLLECTED_AT = pd.Timestamp("2026-10-15")
CENSOR_MONTHS = 3
MAX_PRICE_RATIO = 50
TRAILER_RE = r"прицеп\w*\s+(?:к\s+)?легков|легков\w*\s+прицеп"
SHARE_RE = r"\d\s*/\s*\d+\s*дол[яиюей]|дол[яиюей]\s+в\s+праве\s*\(?\s*\d\s*/\s*\d"
COMMERCIAL = {"GAZ": ("27", "32", "33", "A2", "A3", "A6", "C4", "GAZelle", "Luidor", "2217", "2818", "2834", "3009", "3010", "3035", "53"),
              "UAZ": ("2206", "3303", "3741", "3909", "3962", "452", "23602", "Profi")}
TRUCK_MAKES = {"MAZ", "KAMAZ"}
VIN_YEAR_CODES = "ABCDEFGHJKLMNPRSTVWXY123456789"
VIN_MIN_LOTS = 20
VIN_MIN_AGREEMENT = 0.95


def _is_commercial(lots: pd.DataFrame) -> pd.Series:
    model = lots["model"].fillna("")
    by_model = pd.Series(False, index=lots.index)
    for make, prefixes in COMMERCIAL.items():
        by_model |= (lots["make"] == make) & model.str.startswith(prefixes)
    return by_model | lots["make"].isin(TRUCK_MAKES)


def _last_sale_per_vin(lots: pd.DataFrame) -> pd.Series:
    has_vin = lots["vin_hash"].notna()
    later = lots[has_vin].sort_values("requestTimeBegin").duplicated("vin_hash", keep="last")
    return ~lots.index.isin(later[later].index)


def _last_sale_without_vin(lots: pd.DataFrame) -> pd.Series:
    key = ["debtor_key", "make", "model", "year"]
    known = lots.dropna(subset=key)
    groups = known.groupby(key)
    has_gap = groups["vin_hash"].transform(lambda s: s.isna().any()) & (groups["sale_price"].transform("size") > 1)
    later = known[has_gap].sort_values("requestTimeBegin").duplicated(key, keep="last")
    return ~lots.index.isin(later[later].index)


def _decode_vin_year(code, published_year: int) -> float:
    if not isinstance(code, str) or code.upper() not in VIN_YEAR_CODES:
        return np.nan
    i = VIN_YEAR_CODES.index(code.upper())
    if i >= 21:
        return 2001 + i - 21
    return 2010 + i if 2010 + i <= published_year + 1 else 1980 + i


def add_vin_year(lots: pd.DataFrame) -> pd.DataFrame:
    vin_year = pd.Series([_decode_vin_year(c, y) for c, y in zip(lots["vin_year_code"], lots["requestTimeBegin"].dt.year)],
                         index=lots.index)
    both = lots["year"].notna() & vin_year.notna()
    agree = ((lots["year"] - vin_year).abs() <= 1)[both].groupby(lots["vin_wmi"][both]).agg(["mean", "size"])
    reliable = agree[(agree["size"] >= VIN_MIN_LOTS) & (agree["mean"] >= VIN_MIN_AGREEMENT)].index
    vin_year = vin_year.where(lots["vin_wmi"].isin(reliable))
    source = np.select([lots["year"].notna(), vin_year.notna()], ["текст", "VIN"], "нет")
    return lots.assign(year=lots["year"].fillna(vin_year), year_source=source)


def add_region(lots: pd.DataFrame) -> pd.DataFrame:
    both = lots[["court_code", "lot_regionID"]].dropna()
    court_region = both.groupby("court_code")["lot_regionID"].agg(lambda s: s.value_counts().index[0])
    return lots.assign(region=lots["lot_regionID"].fillna(lots["court_code"].map(court_region)))


def clean(lots: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    text = lots["lot_title"].fillna("") + " " + lots["lot_info"].fillna("")
    rules = {
        f"опубликован до {SINCE.date()}": lots["requestTimeBegin"] >= SINCE,
        f"опубликован позже {CENSOR_MONTHS} мес. до сбора": lots["requestTimeBegin"] <= COLLECTED_AT - pd.DateOffset(months=CENSOR_MONTHS),
        f"цена продажи / начальная > {MAX_PRICE_RATIO}": lots["sale_price"] / lots["lot_priceBegin"] <= MAX_PRICE_RATIO,
        "продаётся доля в праве": ~text.str.contains(SHARE_RE, case=False),
        "прицеп": ~(text.str.contains(TRAILER_RE, case=False) & lots["make"].isna()),
        "грузовой или коммерческий транспорт": ~_is_commercial(lots),
        "повторная продажа того же VIN": _last_sale_per_vin(lots),
        "повторная продажа без VIN (должник, марка, модель, год)": _last_sale_without_vin(lots),
    }
    keep = pd.Series(True, index=lots.index)
    removed = {}
    for name, rule in rules.items():
        removed[name] = int((keep & ~rule).sum())
        keep &= rule
    return lots[keep], pd.Series(removed)


def prepare(cards: pd.DataFrame) -> pd.DataFrame:
    lots = cards[cards["sale_price"].notna() & (cards["n_vins"] <= 1)]
    lots = pd.concat([lots, extract_frame(lots)], axis=1)
    return add_region(add_vin_year(normalize_models(lots, fit=lots["requestTimeBegin"] < TEST_START)))


def build(cards: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    lots, removed = clean(prepare(cards))
    if Path(TRADES_PATH).exists():
        lots = add_first_price(lots, pd.read_parquet(TRADES_PATH))
    lots = lots.assign(log_price=np.log(lots["sale_price"]))
    return lots.reset_index(drop=True), removed


def main() -> None:
    cards = pd.read_parquet(CARDS_PATH)
    lots, removed = build(cards)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lots.to_parquet(OUT_PATH, index=False)
    print(removed.to_string())
    print(f"{len(cards)} cards -> {len(lots)} lots -> {OUT_PATH}")


if __name__ == "__main__":
    main()
