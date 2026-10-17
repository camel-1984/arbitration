import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler

from src.models import catboost_model, ensemble, linear
from src.models.evaluate import CV_QUARTERS, TEST_START, read_lots, sold_at

FIRST_PATH = Path("data/processed/first_auctions.parquet")
PRICE = ["log_first_price", "start_ratio"]
MARKET = ["market_spread"]
MARKET_FOLDS = 5
LOGISTIC_C = 0.1
MIN_FREQUENCY = 5
CB_PARAMS = {"depth": 4, "l2_leaf_reg": 10, "iterations": 300, "learning_rate": 0.05}
CATBOOST_WEIGHT = 0.5
SEED = 42


def read_first(path: Path = FIRST_PATH, until=TEST_START) -> pd.DataFrame:
    lots = pd.read_parquet(path)
    return lots if until is None else lots[lots["requestTimeBegin"] < until].reset_index(drop=True)


def market_quantiles(market_train: pd.DataFrame, lots: pd.DataFrame) -> np.ndarray:
    return np.log(ensemble.predict(market_train, lots)[["p25", "p50", "p75"]].to_numpy())


def with_market(lots: pd.DataFrame, log_q: np.ndarray) -> pd.DataFrame:
    return lots.assign(start_ratio=np.log(lots["first_price"]) - log_q[:, 1], market_spread=log_q[:, 2] - log_q[:, 0])


def oof_market_ratio(train: pd.DataFrame, market_train: pd.DataFrame) -> pd.DataFrame:
    oof = np.full((len(train), 3), np.nan)
    groups = train["debtor_name_key"].fillna("нет")
    for _, held_idx in GroupKFold(MARKET_FOLDS).split(train, groups=groups):
        held = train.iloc[held_idx]
        oof[held_idx] = market_quantiles(market_train[~market_train["debtor_name_key"].isin(held["debtor_name_key"])], held)
    return with_market(train, oof)


def add_market_ratio(train: pd.DataFrame, valid: pd.DataFrame, market_train: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return oof_market_ratio(train, market_train), with_market(valid, market_quantiles(market_train, valid))


def make_logistic():
    preprocess = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=MIN_FREQUENCY), linear.CATEGORICAL),
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()),
         ["age", "log_power", "log_engine"] + PRICE + MARKET),
        ("months", make_pipeline(SimpleImputer(strategy="median"), SplineTransformer(n_knots=3, degree=1, extrapolation="linear")),
         ["months"]),
        ("flags", "passthrough", linear.FLAGS + linear.EXTRA_BINARY),
    ])
    return make_pipeline(preprocess, LogisticRegression(C=LOGISTIC_C, max_iter=5000))


def make_catboost(columns) -> CatBoostClassifier:
    monotone = [-1 if column in PRICE else 0 for column in columns]
    return CatBoostClassifier(**CB_PARAMS, monotone_constraints=monotone, random_seed=SEED, verbose=False, thread_count=-1, allow_writing_files=False)


def lin_features(lots: pd.DataFrame) -> pd.DataFrame:
    x = linear.features(lots)
    return x.assign(**{column: lots[column] for column in PRICE + MARKET if column not in x})


def cb_features(lots: pd.DataFrame) -> pd.DataFrame:
    x = catboost_model.features(lots, with_start=True)
    return x.assign(**{column: lots[column] for column in PRICE + MARKET if column not in x})


def _cb_pool(lots: pd.DataFrame, label=None) -> Pool:
    return Pool(cb_features(lots), label, cat_features=catboost_model.CATEGORICAL)


def fit(train: pd.DataFrame) -> dict:
    y = train["sold_first"].astype(int)
    logistic = make_logistic().fit(lin_features(train), y)
    catboost = make_catboost(cb_features(train).columns).fit(_cb_pool(train, y))
    return {"logistic": logistic, "catboost": catboost}


def predict_proba(models: dict, lots: pd.DataFrame) -> pd.DataFrame:
    p_lin = models["logistic"].predict_proba(lin_features(lots))[:, 1]
    p_cb = models["catboost"].predict_proba(_cb_pool(lots))[:, 1]
    return pd.DataFrame({"logistic": p_lin, "catboost": p_cb, "p_first": CATBOOST_WEIGHT * p_cb + (1 - CATBOOST_WEIGHT) * p_lin},
                        index=lots.index)


def price_curve(models: dict, lot: pd.DataFrame, market_log_q: np.ndarray, prices) -> np.ndarray:
    rows = pd.concat([lot] * len(prices), ignore_index=True).assign(first_price=list(prices))
    return predict_proba(models, with_market(rows, np.tile(market_log_q, (len(prices), 1))))["p_first"].to_numpy()


def time_folds(first: pd.DataFrame, sold: pd.DataFrame, quarters=CV_QUARTERS):
    sold_time = sold_at(sold)
    for quarter in quarters:
        period = pd.Period(quarter, "Q")
        start = period.start_time
        market_train = sold[(sold["requestTimeBegin"] < start) & (sold_time < start)]
        train = first[(first["requestTimeBegin"] < start) & (first["outcome_at"] < start)]
        valid = first[(first["requestTimeBegin"] >= start) & (first["requestTimeBegin"] <= period.end_time)]
        yield quarter, *add_market_ratio(train, valid, market_train)


def metrics(y: pd.Series, p: pd.Series) -> dict:
    y = y.astype(int)
    return {
        "лотов": len(y),
        "доля продаж": y.mean(),
        "средний прогноз": p.mean(),
        "log loss": log_loss(y, p.clip(1e-4, 1 - 1e-4), labels=[0, 1]),
        "brier": brier_score_loss(y, p),
        "AUC": roc_auc_score(y, p) if y.nunique() > 1 else np.nan,
    }


def calibration(y: pd.Series, p: pd.Series, bins: int = 10) -> pd.DataFrame:
    frame = pd.DataFrame({"p": p, "y": y.astype(int)})
    frame["bin"] = pd.qcut(frame["p"], bins, labels=False, duplicates="drop")
    table = frame.groupby("bin").agg(лотов=("p", "size"), прогноз=("p", "mean"), факт=("y", "mean"))
    return table


def cross_validate(first: pd.DataFrame, sold: pd.DataFrame, quarters=CV_QUARTERS) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, parts = [], []
    for quarter, train, valid in time_folds(first, sold, quarters):
        p = predict_proba(fit(train), valid)
        base_rate = train.loc[train["requestTimeBegin"] >= pd.Period(quarter, "Q").start_time - pd.DateOffset(months=12), "sold_first"].mean()
        p["base rate"] = base_rate
        for model in ["base rate", "logistic", "catboost", "p_first"]:
            rows.append({"фолд": quarter, "модель": model, "train": len(train), **metrics(valid["sold_first"], p[model])})
        parts.append(pd.concat([valid[["sold_first", "start_ratio", "requestTimeBegin"]], p], axis=1))
    return pd.DataFrame(rows), pd.concat(parts)


def main() -> None:
    argparse.ArgumentParser().parse_args()
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", "{:.4f}".format)
    first, sold = read_first(), read_lots(ensemble.LOTS_PATH)
    folds, predictions = cross_validate(first, sold)
    print(folds.to_string(index=False), "\n")
    print(folds.groupby("модель")[["log loss", "brier", "AUC", "средний прогноз", "доля продаж"]].mean().sort_values("log loss"), "\n")
    print("калибровка (p_first)\n", calibration(predictions["sold_first"], predictions["p_first"]))


if __name__ == "__main__":
    main()
