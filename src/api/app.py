import json
import re
import threading
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Annotated

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi import Path as PathParam
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.collect.cdtrf import BASE_URL, PASSENGER_CATEGORY, USER_AGENT
from src.features.normalize import _apply_aliases
from src.features.text import extract_features
from src.parse.cdtrf import parse_html

WEB_DIR = Path("web")
CATALOG_PATH = WEB_DIR / "catalog.json"
JOURNAL_PATH = Path("data/pilot/journal.json")
LOT_URL_RE = re.compile(r"torgi\.cdtrf\.ru/(?:[\w-]+/)*trades/(\d{1,9})(?!\d)", re.I)
MAX_TEXT = 20_000
MAX_FORECAST_CHARS = 20_000
MAX_JOURNAL_ENTRIES = 5_000
FIRST_SALE_DATE = date(2020, 1, 1)
Price = Annotated[float, Field(ge=1_000, le=50_000_000)]
Flag = Annotated[int, Field(ge=0, le=1)]
FIELDS = ["make", "model", "year", "power_hp", "engine_cc", "major_defect", "damaged", "no_keys_or_docs", "pledge",
          "arrest_or_ban", "location_unknown"]

app = FastAPI(title="Цена на торгах")
journal_lock = threading.Lock()


def lot_url(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    link = LOT_URL_RE.search(value)
    if not link:
        raise ValueError("нужна ссылка на карточку лота torgi.cdtrf.ru/trades/...")
    return f"{BASE_URL}/trades/{link.group(1)}"


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT)


class Lot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    make: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=60)
    year: int = Field(ge=1960, le=date.today().year + 1)
    region: str | None = Field(default=None, pattern=r"^\d{1,3}$")
    power_hp: float | None = Field(default=None, ge=30, le=1000)
    engine_cc: float | None = Field(default=None, ge=500, le=8500)
    first_price: Price | None = None
    major_defect: Flag = 0
    damaged: Flag = 0
    no_keys_or_docs: Flag = 0
    pledge: Flag = 0
    arrest_or_ban: Flag = 0
    location_unknown: Flag = 0


class PilotEntry(BaseModel):
    lot: Lot
    blind_estimate: Price | None = None
    chosen_price: Price | None = None
    trade_url: str | None = Field(default=None, max_length=300)
    forecast: dict

    _url = field_validator("trade_url")(lot_url)

    @field_validator("forecast")
    @classmethod
    def small_forecast(cls, value: dict) -> dict:
        if len(json.dumps(value)) > MAX_FORECAST_CHARS:
            raise ValueError("прогноз слишком большой")
        return value


class PilotOutcome(BaseModel):
    trade_url: str | None = Field(default=None, max_length=300)
    actual_start_price: Price | None = None
    sold_first: bool | None = None
    sale_price: Price | None = None
    sale_date: date | None = None
    note: str | None = Field(default=None, max_length=2_000)

    _url = field_validator("trade_url")(lot_url)

    @field_validator("sale_date")
    @classmethod
    def past_date(cls, value: date | None) -> date | None:
        if value is not None and not FIRST_SALE_DATE <= value <= date.today():
            raise ValueError("дата продажи должна быть не раньше 2020 года и не позже сегодняшнего дня")
        return value


def _catalog_spelling(make: str | None, model: str | None) -> tuple[str | None, str | None]:
    makes = json.loads(CATALOG_PATH.read_text())["makes"] if CATALOG_PATH.exists() else {}
    by_lower = {m.lower(): m for m in makes}
    make = by_lower.get((make or "").lower(), make)
    models = {m.lower(): m for m in makes.get(make, [])}
    return make, models.get((model or "").lower(), model)


def _fetch_card(trade_id: int) -> dict:
    try:
        response = httpx.get(f"{BASE_URL}/trades/{trade_id}", headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(502, "не удалось загрузить карточку лота") from None
    card = parse_html(response.text)
    if card is None:
        raise HTTPException(502, "карточка лота не распознана")
    return card


def _features(title: str, info: str) -> dict:
    features = extract_features(title, info)
    row = _apply_aliases(pd.DataFrame([{"make": features.get("make"), "model": features.get("model")}])).iloc[0]
    make, model = _catalog_spelling(row["make"] if pd.notna(row["make"]) else None, row["model"] if pd.notna(row["model"]) else None)
    result = {field: features.get(field) for field in FIELDS}
    result.update(make=make, model=model)
    return {key: (None if value is None or (isinstance(value, float) and pd.isna(value)) else value) for key, value in result.items()}


@app.post("/api/extract")
def extract(request: ExtractRequest) -> dict:
    link = LOT_URL_RE.search(request.text)
    if not link:
        return _features("", request.text)
    card = _fetch_card(int(link.group(1)))
    result = _features(card["lot_title"] or "", card["lot_info"] or "")
    is_auction = "аукцион" in (card["tradeTypeDescription"] or "").lower()
    region = card["lot_regionID"]
    result.update(
        region=str(int(region)) if region is not None else None,
        first_price=card["lot_priceBegin"] if is_auction else None,
        description="\n".join(filter(None, [card["lot_title"], card["lot_info"]])),
        source={"trade_id": card["tradeId"], "trade_type": card["tradeTypeDescription"], "url": f"{BASE_URL}/trades/{card['tradeId']}",
                "passenger": list(card["lot_categoryIDs"] or []) == [PASSENGER_CATEGORY]},
    )
    return result


@app.post("/api/predict")
def predict() -> None:
    raise HTTPException(501, "модели ещё не подключены")


def _read_journal() -> list[dict]:
    return json.loads(JOURNAL_PATH.read_text()) if JOURNAL_PATH.exists() else []


def _write_journal(entries: list[dict]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=1))
    tmp.replace(JOURNAL_PATH)


@app.get("/api/pilot")
def pilot_list() -> list[dict]:
    return _read_journal()


@app.post("/api/pilot")
def pilot_add(entry: PilotEntry) -> dict:
    outcome = PilotOutcome().model_dump(mode="json")
    outcome.pop("trade_url")
    record = {"id": uuid.uuid4().hex[:8], "created_at": datetime.now().isoformat(timespec="seconds"),
              **entry.model_dump(mode="json"), "outcome": outcome}
    with journal_lock:
        entries = _read_journal()
        if len(entries) >= MAX_JOURNAL_ENTRIES:
            raise HTTPException(507, "журнал переполнен")
        entries.append(record)
        _write_journal(entries)
    return record


@app.patch("/api/pilot/{entry_id}")
def pilot_outcome(entry_id: Annotated[str, PathParam(pattern=r"^[0-9a-f]{8}$")], outcome: PilotOutcome) -> dict:
    with journal_lock:
        entries = _read_journal()
        record = next((e for e in entries if e["id"] == entry_id), None)
        if record is None:
            raise HTTPException(404, "запись не найдена")
        update = outcome.model_dump(mode="json")
        trade_url = update.pop("trade_url")
        if trade_url:
            record["trade_url"] = trade_url
        record["outcome"] = update
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _write_journal(entries)
    return record


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
