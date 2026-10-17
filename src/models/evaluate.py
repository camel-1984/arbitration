import numpy as np
import pandas as pd

QUANTILES = (0.25, 0.5, 0.75)
CV_QUARTERS = ["2025Q1", "2025Q2", "2025Q3", "2025Q4"]
TEST_START = pd.Timestamp("2026-01-01")
QUANTILE_COLUMNS = [f"p{int(q * 100)}" for q in QUANTILES]


def read_lots(path) -> pd.DataFrame:
    lots = pd.read_parquet(path)
    lots["stage"] = np.where(lots["tradeTypeDescription"].str.contains("аукцион|конкурс"), "аукцион", "публичное предложение")
    return lots


def set_display() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.float_format", "{:.3f}".format)


def sold_at(lots: pd.DataFrame) -> pd.Series:
    return pd.concat([lots["winnerTime"].fillna(lots["auctionTimeBegin"]), lots["salesContractTime"]], axis=1).max(axis=1)


def time_folds(lots: pd.DataFrame, quarters=CV_QUARTERS):
    published, sold = lots["requestTimeBegin"], sold_at(lots)
    for quarter in quarters:
        period = pd.Period(quarter, "Q")
        start, end = period.start_time, period.end_time
        yield quarter, lots[(published < start) & (sold < start)], lots[(published >= start) & (published <= end)]


def pinball(y: np.ndarray, pred: np.ndarray, q: float) -> float:
    diff = y - pred
    return float(np.mean(np.maximum(q * diff, (q - 1) * diff)))


def metrics(price: pd.Series, pred: pd.DataFrame) -> dict:
    ape = (pred["p50"] - price).abs() / price
    log_y = np.log(price.to_numpy())
    return {
        "лотов": len(price),
        "MdAPE": ape.median(),
        "промах > 50%": (ape > 0.5).mean(),
        "покрытие P25-P75": ((price >= pred["p25"]) & (price <= pred["p75"])).mean(),
        "ширина коридора": ((pred["p75"] - pred["p25"]) / pred["p50"]).median(),
        "pinball (log)": np.mean([pinball(log_y, np.log(pred[column].to_numpy()), q) for q, column in zip(QUANTILES, QUANTILE_COLUMNS)]),
    }


def cross_validate(predict, lots: pd.DataFrame, quarters=CV_QUARTERS) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, parts = [], []
    for quarter, train, valid in time_folds(lots, quarters):
        pred = predict(train, valid)
        rows.append({"фолд": quarter, "train": len(train), **metrics(valid["sale_price"], pred)})
        parts.append(pd.concat([valid, pred], axis=1))
    folds = pd.DataFrame(rows).set_index("фолд")
    folds.loc["среднее"] = folds.mean()
    return folds, pd.concat(parts)


def breakdown(predictions: pd.DataFrame, by: str) -> pd.DataFrame:
    return pd.DataFrame({key: metrics(g["sale_price"], g) for key, g in predictions.groupby(by)}).T.sort_values("лотов", ascending=False)
