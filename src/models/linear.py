import argparse
from functools import partial
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import QuantileRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

from src.models.evaluate import QUANTILE_COLUMNS, QUANTILES, breakdown, cross_validate, read_lots, set_display

LOTS_PATH = Path("data/processed/lots.parquet")
FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"]
CATEGORICAL = ["make", "make_model", "region", "debtType"]
NUMERIC = ["age", "log_power", "log_engine", "months"]
EXTRA_BINARY = ["has_images"]
START = ["log_first_price"]
TREND_KNOTS = 3
MIN_FREQUENCY = 2
ALPHA = 3e-5
ALPHA_GRID = [0, 1e-5, 1e-4, 1e-3, 1e-2]
MIN_FREQUENCY_GRID = [3, 5, 10, 20]


def base_features(lots: pd.DataFrame) -> dict:
    published = lots["requestTimeBegin"]
    return {
        "make": lots["make"].fillna("нет"),
        "make_model": (lots["make"] + " " + lots["model"]).fillna("нет"),
        "region": lots["region"].fillna("нет"),
        "debtType": lots["debtType"].fillna("нет"),
        "age": (published.dt.year - lots["year"]).clip(0, 50),
        "log_power": np.log(lots["power_hp"]),
        "log_engine": np.log(lots["engine_cc"]),
        "months": (published.dt.year - 2024) * 12 + published.dt.month,
        "has_images": (lots["n_images"] > 0).astype(int),
        "log_first_price": np.log(lots["first_price"]) if "first_price" in lots else np.nan,
        "start_ratio": lots["start_ratio"] if "start_ratio" in lots else np.nan,
    }


def features(lots: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({**base_features(lots), **{flag: lots[flag] for flag in FLAGS}}, index=lots.index)


def make_model(q: float, alpha: float = ALPHA, min_frequency: int = MIN_FREQUENCY, with_start: bool = False):
    preprocess = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=min_frequency), CATEGORICAL),
        ("age", make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                              ColumnTransformer([("spline", SplineTransformer(n_knots=5, degree=3), [0])], remainder="passthrough")), ["age"]),
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()),
         ["log_power", "log_engine"] + (START if with_start else [])),
        ("months", make_pipeline(SimpleImputer(strategy="median"),
                                 SplineTransformer(n_knots=TREND_KNOTS, degree=1, extrapolation="linear")), ["months"]),
        ("flags", "passthrough", FLAGS + EXTRA_BINARY),
    ] + ([("ratio", make_pipeline(SimpleImputer(strategy="median"), SplineTransformer(n_knots=6, degree=3)), ["start_ratio"])]
         if with_start else []))
    return make_pipeline(preprocess, QuantileRegressor(quantile=q, alpha=alpha, solver="highs"))


def predict(train: pd.DataFrame, valid: pd.DataFrame, **params) -> pd.DataFrame:
    x_train, x_valid = features(train), features(valid)
    preds = [np.exp(make_model(q, **params).fit(x_train, train["log_price"]).predict(x_valid)) for q in QUANTILES]
    return pd.DataFrame(np.sort(np.column_stack(preds), axis=1), index=valid.index, columns=QUANTILE_COLUMNS)


def tune(lots: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for alpha, min_frequency in product(ALPHA_GRID, MIN_FREQUENCY_GRID):
        folds, _ = cross_validate(partial(predict, alpha=alpha, min_frequency=min_frequency), lots)
        rows.append({"alpha": alpha, "min_frequency": min_frequency, **folds.loc["среднее"].drop(["train", "лотов"])})
        print(rows[-1], flush=True)
    return pd.DataFrame(rows).sort_values("pinball (log)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tune", action="store_true")
    args = parser.parse_args()
    lots = read_lots(LOTS_PATH)
    set_display()
    if args.tune:
        print(tune(lots))
        return
    folds, predictions = cross_validate(predict, lots)
    print(folds, "\n")
    print(breakdown(predictions, "stage"))


if __name__ == "__main__":
    main()
