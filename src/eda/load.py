from pathlib import Path

import numpy as np
import pandas as pd

from src.dataset.build import prepare

CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")


def load_cards(path: Path = CARDS_PATH) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["year_published"] = df["requestTimeBegin"].dt.year
    df["price_ratio"] = df["sale_price"] / df["lot_priceBegin"]
    df["days_to_contract"] = (df["salesContractTime"] - df["declarateTime"]).dt.days
    return df


def load_lots(since: str = "2024-01-01", path: Path = CARDS_PATH) -> pd.DataFrame:
    df = prepare(pd.read_parquet(path))
    df = df[df["requestTimeBegin"] >= since].reset_index(drop=True)
    df["log_price"] = np.log(df["sale_price"])
    df["year_published"] = df["requestTimeBegin"].dt.year
    df["quarter"] = df["requestTimeBegin"].dt.to_period("Q").astype(str)
    df["price_ratio"] = df["sale_price"] / df["lot_priceBegin"]
    df["age"] = df["year_published"] - df["year"]
    df["stage"] = df["tradeTypeDescription"].str.contains("аукцион|конкурс").map({True: "аукцион", False: "публичное предложение"})
    return df
