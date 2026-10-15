import argparse
from pathlib import Path

import pandas as pd

GOLD_XLSX = Path("data/labels/gold_to_fill.xlsx")
GOLD_CSV = Path("labels/gold.csv")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, help="e.g. dev, test, test2")
    parser.add_argument("--annotator", required=True, choices=["human", "claude"])
    args = parser.parse_args()

    new = pd.read_excel(GOLD_XLSX).drop(columns=["lot_title", "lot_info"])
    new.insert(1, "split", args.split)
    new.insert(2, "annotator", args.annotator)
    gold = pd.read_csv(GOLD_CSV) if GOLD_CSV.exists() else new.iloc[:0]
    new = new[~new["tradeId"].isin(gold["tradeId"])]
    pd.concat([gold, new], ignore_index=True).to_csv(GOLD_CSV, index=False)
    print(f"added {len(new)} lots as {args.split}/{args.annotator}, total {len(gold) + len(new)} -> {GOLD_CSV}")


if __name__ == "__main__":
    main()
