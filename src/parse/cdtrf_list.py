import json
from pathlib import Path

import pandas as pd

from src.features.text import extract_make, extract_model
from src.parse.cdtrf import clean_text, debtor_name_key, find_vins, short_hash, title_key

LIST_DIR = Path("data/raw/cdtrf/list_all")
OUT_PATH = Path("data/interim/cdtrf_trades.parquet")


def parse_item(item: dict) -> dict:
    title = clean_text(item.get("name"))
    vins = find_vins(item.get("name"))
    make = extract_make(title or "")
    return {
        "tradeId": item["tradeId"],
        "tradeType": item["tradeTypeDescription"],
        "status": item["tradeStatusDescription"],
        "price": item["actualPrice"],
        "requestTimeBegin": pd.Timestamp(item["requestTimeBegin"]),
        "categories": item["categories"],
        "debtor_name_key": debtor_name_key(item),
        "title_key": title_key(title),
        "title_vin_hash": short_hash(vins[0]) if vins else None,
        "title_make": make,
        "title_model": extract_model([title or ""], make),
    }


def main() -> None:
    items = {}
    for path in sorted(LIST_DIR.glob("*.json")):
        for item in json.loads(path.read_text())["items"]:
            items[item["tradeId"]] = item
    df = pd.DataFrame([parse_item(item) for item in items.values()])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT_PATH, index=False)
    print(f"{len(df)} trades -> {OUT_PATH}")
    print(df["status"].value_counts().to_string())


if __name__ == "__main__":
    main()
