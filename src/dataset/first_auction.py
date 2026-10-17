from pathlib import Path

import pandas as pd

from src.dataset.build import CARDS_PATH, SHARE_RE, SINCE, TEST_START, TRAILER_RE, _is_commercial, add_region, add_vin_year
from src.dataset.stages import TRADES_PATH, first_auctions
from src.features.normalize import normalize_models
from src.features.text import extract_frame

FIRST_CARDS_PATH = Path("data/interim/cdtrf_first_cards.parquet")
OUT_PATH = Path("data/processed/first_auctions.parquet")
FINAL_STATUSES = {"SignContract", "NotHeld", "Complete"}


def build(first_cards: pd.DataFrame, sold_cards: pd.DataFrame, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    firsts = first_auctions(trades)
    firsts = firsts[firsts["requestTimeBegin"] >= SINCE]
    cards = pd.concat([first_cards, sold_cards]).drop_duplicates("tradeId")
    cards = cards[cards["tradeId"].isin(firsts["tradeId"])].reset_index(drop=True)
    lots = pd.concat([cards, extract_frame(cards)], axis=1)
    lots = add_region(add_vin_year(normalize_models(lots, fit=lots["requestTimeBegin"] < TEST_START)))
    text = lots["lot_title"].fillna("") + " " + lots["lot_info"].fillna("")
    rules = {
        "исход не известен": lots["tradeStatus"].isin(FINAL_STATUSES),
        "несколько VIN": lots["n_vins"] <= 1,
        "продаётся доля в праве": ~text.str.contains(SHARE_RE, case=False),
        "прицеп": ~(text.str.contains(TRAILER_RE, case=False) & lots["make"].isna()),
        "грузовой или коммерческий транспорт": ~_is_commercial(lots),
    }
    keep = pd.Series(True, index=lots.index)
    removed = {}
    for name, rule in rules.items():
        removed[name] = int((keep & ~rule).sum())
        keep &= rule
    lots = lots[keep].assign(
        sold_first=lambda d: d["tradeStatus"] == "SignContract",
        first_price=lambda d: d["lot_priceBegin"],
        outcome_at=lambda d: d["auctionTimeBegin"].fillna(d["requestTimeEnd"]),
    )
    return lots.reset_index(drop=True), pd.Series(removed)


def main() -> None:
    lots, removed = build(pd.read_parquet(FIRST_CARDS_PATH), pd.read_parquet(CARDS_PATH), pd.read_parquet(TRADES_PATH))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lots.to_parquet(OUT_PATH, index=False)
    print(removed.to_string())
    print(f"{len(lots)} first auctions -> {OUT_PATH}")
    before_test = lots[lots["requestTimeBegin"] < TEST_START]
    print(before_test.groupby(before_test["requestTimeBegin"].dt.year)["sold_first"].agg(["size", "mean"]).round(3).to_string())


if __name__ == "__main__":
    main()
