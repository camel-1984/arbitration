import argparse
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from src.models import catboost_model, linear
from src.models.evaluate import breakdown, cross_validate, read_lots, set_display

LOTS_PATH = Path("data/processed/lots.parquet")
CATBOOST_WEIGHT = 0.5
WIDTH_K = {False: 1.12, True: 1.15}
MARKET_FOLDS = 5
SEED = 0


def _market(train: pd.DataFrame, valid: pd.DataFrame) -> np.ndarray:
    return linear.make_model(0.5).fit(linear.features(train), train["log_price"]).predict(linear.features(valid))


def add_start_ratio(train: pd.DataFrame, valid: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    oof = np.zeros(len(train))
    for fit_idx, pred_idx in KFold(MARKET_FOLDS, shuffle=True, random_state=SEED).split(train):
        oof[pred_idx] = _market(train.iloc[fit_idx], train.iloc[pred_idx])
    return (train.assign(start_ratio=np.log(train["first_price"]) - oof),
            valid.assign(start_ratio=np.log(valid["first_price"]) - _market(train, valid)))


def predict(train: pd.DataFrame, valid: pd.DataFrame, with_start: bool = False, width_k: float | None = None) -> pd.DataFrame:
    if with_start:
        train, valid = add_start_ratio(train, valid)
    lin = linear.predict(train, valid, with_start=with_start)
    cb = catboost_model.predict(train, valid, with_start=with_start)
    log_q = np.sort(CATBOOST_WEIGHT * np.log(cb.to_numpy()) + (1 - CATBOOST_WEIGHT) * np.log(lin.to_numpy()), axis=1)
    p50 = log_q[:, [1]]
    log_q = p50 + (WIDTH_K[with_start] if width_k is None else width_k) * (log_q - p50)
    return pd.DataFrame(np.exp(log_q), index=valid.index, columns=lin.columns)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-start", action="store_true", help="add the start price of the first auction as a feature")
    args = parser.parse_args()
    lots = read_lots(LOTS_PATH)
    set_display()
    folds, predictions = cross_validate(partial(predict, with_start=args.with_start), lots)
    print(folds, "\n")
    print(breakdown(predictions, "stage"))


if __name__ == "__main__":
    main()
