from pathlib import Path

import numpy as np
import pandas as pd

from src.features.text import extract_frame

CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")
OUT_PATH = Path("data/processed/lots.parquet")


def build(cards: pd.DataFrame) -> pd.DataFrame:
    lots = cards[cards["sale_price"].notna() & (cards["n_vins"] <= 1)]
    lots = pd.concat([lots, extract_frame(lots)], axis=1)
    lots["log_price"] = np.log(lots["sale_price"])
    return lots.reset_index(drop=True)


def main() -> None:
    cards = pd.read_parquet(CARDS_PATH)
    lots = build(cards)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lots.to_parquet(OUT_PATH, index=False)
    print(f"{len(cards)} cards -> {len(lots)} lots -> {OUT_PATH}")


if __name__ == "__main__":
    main()
