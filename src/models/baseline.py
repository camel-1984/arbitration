from pathlib import Path

import numpy as np
import pandas as pd

from src.models.evaluate import QUANTILE_COLUMNS, QUANTILES, breakdown, cross_validate, read_lots, set_display

LOTS_PATH = Path("data/processed/lots.parquet")
MIN_COMPARABLES = 5
LEVELS = [
    ("марка+модель, год ±1", ["make", "model"], 1),
    ("марка+модель, год ±3", ["make", "model"], 3),
    ("марка+модель", ["make", "model"], None),
    ("марка, год ±2", ["make"], 2),
    ("год ±1", [], 1),
    ("все лоты", [], None),
]


def _comparables(train: pd.DataFrame, lot: pd.Series) -> tuple[str, pd.Series]:
    for name, keys, years in LEVELS:
        if any(pd.isna(lot[k]) for k in keys) or (years is not None and pd.isna(lot["year"])):
            continue
        mask = np.ones(len(train), dtype=bool)
        for k in keys:
            mask &= (train[k] == lot[k]).to_numpy()
        if years is not None:
            mask &= ((train["year"] - lot["year"]).abs() <= years).to_numpy()
        if mask.sum() >= MIN_COMPARABLES:
            return name, train["sale_price"][mask]
    return "все лоты", train["sale_price"]


def predict(train: pd.DataFrame, valid: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, lot in valid.iterrows():
        level, prices = _comparables(train, lot)
        rows.append({"уровень": level, **{column: prices.quantile(q) for q, column in zip(QUANTILES, QUANTILE_COLUMNS)}})
    return pd.DataFrame(rows, index=valid.index)


def main() -> None:
    lots = read_lots(LOTS_PATH)
    set_display()
    folds, predictions = cross_validate(predict, lots)
    print(folds, "\n")
    print(breakdown(predictions, "уровень"), "\n")
    print(breakdown(predictions, "stage"))


if __name__ == "__main__":
    main()
