import argparse
from pathlib import Path

import pandas as pd

from src.features import llm, text
from src.features.text import FLAG_PATTERNS

GOLD_PATH = Path("labels/gold.csv")
CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")
VALUE_FIELDS = {"make": 0, "model": 0, "year": 0.1, "power_hp": 0.5, "engine_cc": 1}


def normalize(value) -> str | None:
    if pd.isna(value):
        return None
    return str(value).lower().replace(" ", "").replace("-", "")


def is_correct(gold: pd.Series, pred: pd.Series, tolerance: float) -> pd.Series:
    if tolerance:
        return (gold.astype(float) - pred.astype(float)).abs() <= tolerance
    return gold.map(normalize) == pred.map(normalize)


def value_metrics(gold: pd.Series, pred: pd.Series, tolerance: float) -> dict:
    has_gold = gold.notna()
    correct = is_correct(gold, pred, tolerance)
    return {
        "в эталоне": int(has_gold.sum()),
        "извлечено верно": round(correct[has_gold].mean(), 2),
        "извлечено неверно": int((has_gold & pred.notna() & ~correct).sum()),
        "пропущено": int((has_gold & pred.isna()).sum()),
        "лишнее": int((~has_gold & pred.notna()).sum()),
    }


def flag_metrics(gold: pd.Series, pred: pd.Series) -> dict:
    gold = gold.fillna(0).astype(int)
    tp = int(((gold == 1) & (pred == 1)).sum())
    fp = int(((gold == 0) & (pred == 1)).sum())
    fn = int(((gold == 1) & (pred == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else float("nan")
    recall = tp / (tp + fn) if tp + fn else float("nan")
    return {"в эталоне": int(gold.sum()), "TP": tp, "FP": fp, "FN": fn,
            "precision": round(precision, 2), "recall": round(recall, 2)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="all", help="split name from gold.csv (dev, test, ...) or all")
    parser.add_argument("--extractor", choices=["regex", "llm"], default="regex")
    args = parser.parse_args()

    texts = pd.read_parquet(CARDS_PATH, columns=["tradeId", "lot_title", "lot_info"])
    gold = pd.read_csv(GOLD_PATH).merge(texts, on="tradeId", how="left")
    if args.split != "all":
        gold = gold[gold["split"] == args.split]
    gold = gold[gold["exclude"].fillna(0) != 1]
    pred = (llm if args.extractor == "llm" else text).extract_frame(gold)

    pd.set_option("display.width", 200)
    print(f"лотов: {len(gold)}\n")
    print(pd.DataFrame({f: value_metrics(gold[f], pred[f], t) for f, t in VALUE_FIELDS.items()}).T, "\n")
    print(pd.DataFrame({f: flag_metrics(gold[f], pred[f]) for f in FLAG_PATTERNS}).T, "\n")

    print("Расхождения:")
    for field, tolerance in VALUE_FIELDS.items():
        g, p = gold[field], pred[field]
        bad = ~is_correct(g, p, tolerance)
        if tolerance:
            bad &= g.notna() | p.notna()
        for i in gold.index[bad]:
            print(f"  {gold.at[i, 'tradeId']} {field}: эталон={g[i]} извлечено={p[i]}")
    for field in FLAG_PATTERNS:
        g = gold[field].fillna(0).astype(int)
        for i in gold.index[g != pred[field]]:
            print(f"  {gold.at[i, 'tradeId']} {field}: эталон={g[i]} извлечено={pred.at[i, field]}")


if __name__ == "__main__":
    main()
