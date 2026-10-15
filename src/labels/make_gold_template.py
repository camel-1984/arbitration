import argparse
from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment

CARDS_PATH = Path("data/interim/cdtrf_cards.parquet")
OUT_PATH = Path("data/labels/gold_to_fill.xlsx")

NUMERIC_COLUMNS = ["power_hp", "engine_cc"]
FLAG_COLUMNS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prelabel", type=Path, help="csv with tradeId, make, model, year, exclude, comment")
    args = parser.parse_args()

    cards = pd.read_parquet(CARDS_PATH, columns=["tradeId", "lot_title", "lot_info"])
    prelabel = pd.read_csv(args.prelabel, dtype={"year": "Int64", "exclude": "Int64"})
    missing = set(prelabel["tradeId"]) - set(cards["tradeId"])
    if missing:
        raise ValueError(f"no card for {sorted(missing)}")

    gold = prelabel.merge(cards, on="tradeId", how="left")
    for column in NUMERIC_COLUMNS + FLAG_COLUMNS:
        gold[column] = pd.NA
    if OUT_PATH.exists():
        filled = pd.read_excel(OUT_PATH).rename(columns={"not_running": "major_defect"}).set_index("tradeId")
        gold = gold.set_index("tradeId")
        gold.update(filled[[c for c in filled.columns if c in gold.columns and c not in ("lot_title", "lot_info")]])
        gold = gold.reset_index()
    label_columns = ["make", "model", "year", "exclude", *NUMERIC_COLUMNS, *FLAG_COLUMNS, "comment"]
    gold = gold[["tradeId", "lot_title", "lot_info", *label_columns]]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
        gold.to_excel(writer, index=False)
        sheet = writer.sheets["Sheet1"]
        sheet.freeze_panes = "D2"
        widths = {"A": 9, "B": 35, "C": 80, "D": 14, "E": 16, "F": 7, "G": 8, "R": 40}
        for column in sheet.columns:
            letter = column[0].column_letter
            sheet.column_dimensions[letter].width = widths.get(letter, 11)
            for cell in column:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    print(f"{len(gold)} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
