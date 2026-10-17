import argparse
from functools import partial
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool

from src.models import linear
from src.models.evaluate import QUANTILE_COLUMNS, QUANTILES, breakdown, cross_validate, read_lots, set_display

LOTS_PATH = Path("data/processed/lots.parquet")
FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"]
CATEGORICAL = ["make", "make_model", "region", "debtType", "arbman_sro"]
NUMERIC = ["age", "log_power", "log_engine", "months", "has_images"]
START = ["log_first_price", "start_ratio"]
CTR = ["Borders:TargetBorderCount=15", "Counter"]
PARAMS = {"depth": 4, "l2_leaf_reg": 10, "iterations": 1500, "learning_rate": 0.05, "simple_ctr": CTR, "combinations_ctr": CTR}
GRID = {"depth": [4, 6, 8], "l2_leaf_reg": [3, 10], "iterations": [500, 1500]}
SEED = 42


def features(lots: pd.DataFrame, with_start: bool = False) -> pd.DataFrame:
    columns = {**linear.base_features(lots), "arbman_sro": lots["arbman_sro"].fillna("нет"), **{flag: lots[flag] for flag in FLAGS}}
    return pd.DataFrame(columns, index=lots.index)[CATEGORICAL + NUMERIC + (START if with_start else []) + FLAGS]


def make_model(**params) -> CatBoostRegressor:
    alphas = ",".join(str(q) for q in QUANTILES)
    return CatBoostRegressor(loss_function=f"MultiQuantile:alpha={alphas}", random_seed=SEED, verbose=False, allow_writing_files=False,
                             thread_count=-1, **{**PARAMS, **params})


def predict(train: pd.DataFrame, valid: pd.DataFrame, with_start: bool = False, **params) -> pd.DataFrame:
    model = make_model(**params).fit(Pool(features(train, with_start), train["log_price"], cat_features=CATEGORICAL))
    raw = model.predict(Pool(features(valid, with_start), cat_features=CATEGORICAL))
    return pd.DataFrame(np.sort(np.exp(raw), axis=1), index=valid.index, columns=QUANTILE_COLUMNS)


def tune(lots: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for values in product(*GRID.values()):
        params = dict(zip(GRID, values))
        folds, _ = cross_validate(partial(predict, **params), lots)
        rows.append({**params, **folds.loc["среднее"].drop(["train", "лотов"])})
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
