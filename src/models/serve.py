import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.models import comparables, ensemble, explain, first_sale
from src.models.evaluate import sold_at
from src.models.train_final import BUNDLE_PATH, HISTORY_PATH

CATALOG_PATH = Path("web/catalog.json")
TRADE_URL = "https://torgi.cdtrf.ru/trades/{}"
LADDER_STEPS = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
YEAR_GAP = 2
MIN_CLOSE = 3
MAX_GAP = 2.0
EXPENSIVE = 1_500_000
MAX_GAP_EXPENSIVE = 1.5
N_FACTORS = 6
MIN_EFFECT = 0.01
DEFAULT_DEBT_TYPE = "Nat"
FLAG_LABELS = {
    "major_defect": "Серьёзная техническая неисправность",
    "damaged": "Повреждения кузова",
    "no_keys_or_docs": "Нет ключей или документов",
    "pledge": "Залог",
    "arrest_or_ban": "Арест или запрет",
    "location_unknown": "Местонахождение неизвестно",
}


def load() -> dict:
    bundle = joblib.load(BUNDLE_PATH)
    bundle["history"] = pd.read_parquet(HISTORY_PATH)
    regions = json.loads(CATALOG_PATH.read_text())["regions"] if CATALOG_PATH.exists() else []
    bundle["region_names"] = {r["id"]: r["name"] for r in regions}
    return bundle


def round_price(value: float) -> int:
    step = 10_000 if value >= 200_000 else 5_000 if value >= 50_000 else 1_000
    return int(round(value / step) * step)


def _thousands(value: float) -> int:
    return int(round(value / 1_000) * 1_000)


def _number(value) -> float:
    return np.nan if value is None else float(value)


def lot_frame(lot: dict) -> pd.DataFrame:
    row = {
        "make": lot["make"], "model": lot["model"], "year": int(lot["year"]), "region": lot.get("region"),
        "power_hp": _number(lot.get("power_hp")), "engine_cc": _number(lot.get("engine_cc")),
        "first_price": _number(lot.get("first_price")),
        "debtType": lot.get("debt_type") or DEFAULT_DEBT_TYPE, "n_images": lot.get("n_images") or 0,
        "arbman_sro": lot.get("arbman_sro"), "requestTimeBegin": pd.Timestamp.now().normalize(),
        **{flag: int(lot.get(flag) or 0) for flag in FLAG_LABELS},
    }
    return pd.DataFrame([row])


def _quartiles(frame: pd.DataFrame, rounding) -> dict:
    return {column: rounding(frame[column].iloc[0]) for column in ["p25", "p50", "p75"]}


def _years(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "год"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "года"
    return "лет"


def _factor_label(group: str, lot: dict, x: pd.DataFrame, region_names: dict) -> str | None:
    if group in FLAG_LABELS:
        return FLAG_LABELS[group] if lot.get(group) else None
    if group == "возраст":
        age = int(x["requestTimeBegin"].dt.year.iloc[0] - lot["year"])
        return f"Возраст: {age} {_years(age)}"
    if group == "марка и модель":
        return f"Марка и модель: {lot['make']} {lot['model']}"
    if group == "регион":
        return f"Регион: {region_names.get(lot['region'], lot['region'])}" if lot.get("region") else None
    if group == "мощность":
        return f"Мощность: {lot['power_hp']:.0f} л. с." if lot.get("power_hp") else "Мощность не указана"
    if group == "объём двигателя":
        return f"Объём двигателя: {lot['engine_cc']:.0f} см³" if lot.get("engine_cc") else "Объём двигателя не указан"
    return None


def factors(bundle: dict, lot: dict, x: pd.DataFrame) -> list[dict]:
    effects = np.exp(explain.contributions(bundle["market"]["linear"][1], x).iloc[0] - bundle["factor_base"]) - 1
    rows = []
    for group, effect in effects.items():
        label = _factor_label(group, lot, x, bundle["region_names"])
        if label and abs(effect) >= MIN_EFFECT:
            rows.append({"label": label, "effect": round(float(effect), 3)})
    return sorted(rows, key=lambda row: -abs(row["effect"]))[:N_FACTORS]


def similar_lots(bundle: dict, lot: dict, x: pd.DataFrame) -> list[dict]:
    history = _history(bundle, lot)
    found = comparables.comparables(history, x.iloc[0], pd.Timestamp.now())
    dates = sold_at(history.loc[found.index])
    return [{"make": row["make"], "model": row["model"], "year": None if pd.isna(row["year"]) else int(row["year"]),
             "sale_date": dates.loc[i].date().isoformat(), "sale_price": _thousands(row["sale_price"]), "url": TRADE_URL.format(row["tradeId"])}
            for i, row in found.iterrows()]


def _history(bundle: dict, lot: dict) -> pd.DataFrame:
    history = bundle["history"]
    return history[history["tradeId"] != lot["trade_id"]] if lot.get("trade_id") else history


def close_sales(history: pd.DataFrame, lot: dict) -> pd.Series:
    known = history[sold_at(history) < pd.Timestamp.now()]
    near = (known["make"] == lot["make"]) & (known["model"] == lot["model"]) & ((known["year"] - lot["year"]).abs() <= YEAR_GAP)
    return known.loc[near, "sale_price"]


def _rubles(value: float) -> str:
    return f"{_thousands(value):,}".replace(",", " ") + " ₽"


def _sales_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "продажа"
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return "продажи"
    return "продаж"


def abstain_reason(lot: dict, close: pd.Series, p50: float) -> str | None:
    gap = np.exp(abs(np.log(p50 / close.median()))) if len(close) else np.nan
    if not (gap > MAX_GAP or p50 > EXPENSIVE and (len(close) < MIN_CLOSE or gap > MAX_GAP_EXPENSIVE)):
        return None
    car = f"{lot['make']} {lot['model']} {lot['year'] - YEAR_GAP}-{lot['year'] + YEAR_GAP} годов выпуска"
    if len(close) == 0:
        return f"В истории торгов нет ни одной продажи {car}."
    if len(close) < MIN_CLOSE:
        return f"В истории торгов всего {len(close)} {_sales_word(len(close))} {car}, для дорогой машины этого мало."
    return (f"Цены прошлых продаж {car} сильно расходятся с оценкой модели: "
            f"медиана {_rubles(close.median())}, продаж в истории: {len(close)}.")


def predict(bundle: dict, lot: dict) -> dict:
    x = lot_frame(lot)
    market = ensemble.predict_fitted(bundle["market"], x)
    close = close_sales(_history(bundle, lot), lot)
    typical = ensemble.predict_fitted(bundle["typical"], x)
    typical_price = round_price(typical["p50"].iloc[0])
    own = lot.get("first_price")
    prices = sorted({round_price(typical_price * k) for k in LADDER_STEPS} | ({int(own)} if own else set()))
    p_first = first_sale.price_curve(bundle["first_sale"], x, np.log(market.to_numpy()[0]), prices)
    sale = ensemble.predict_fitted(bundle["market_start"], pd.concat([x] * len(prices), ignore_index=True).assign(first_price=prices))
    curve = [{"price": price, "p_first": round(float(p), 4), "sale": {c: _thousands(sale[c].iloc[i]) for c in ["p25", "p50", "p75"]},
              "typical": price == typical_price, "own": bool(own) and price == int(own)}
             for i, (price, p) in enumerate(zip(prices, p_first))]
    return {
        "demo": False,
        "data_until": bundle["data_until"],
        "typical_start": {**_quartiles(typical, round_price), "p50": typical_price},
        "market": _quartiles(market, _thousands),
        "curve": curve,
        "abstain": abstain_reason(lot, close, market["p50"].iloc[0]),
        "low_reliability": len(close) == 0,
        "factors": factors(bundle, lot, x),
        "comparables": similar_lots(bundle, lot, x),
    }
