from pathlib import Path

import pandas as pd

CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")


def load_cards(path: Path = CARDS_PATH) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["year_published"] = df["requestTimeBegin"].dt.year
    df["price_ratio"] = df["sale_price"] / df["lot_priceBegin"]
    df["days_to_contract"] = (df["salesContractTime"] - df["declarateTime"]).dt.days
    return df
