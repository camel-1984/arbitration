import numpy as np
import pandas as pd

from src.models.evaluate import sold_at

N_COMPARABLES = 5
MAX_YEAR_GAP = 2
DEFECT_FLAGS = ["major_defect", "damaged", "no_keys_or_docs"]
COLUMNS = ["tradeId", "make", "model", "year", "sale_price", "requestTimeBegin", "tradeTypeDescription", *DEFECT_FLAGS]


def comparables(history: pd.DataFrame, lot: pd.Series, at: pd.Timestamp, n: int = N_COMPARABLES) -> pd.DataFrame:
    known = history[sold_at(history) < at]
    for keys in (["make", "model"], ["make"]):
        if any(pd.isna(lot.get(k)) for k in keys):
            continue
        pool = known[(known[keys] == lot[keys]).all(axis=1)]
        if len(pool) >= n:
            break
    else:
        return known.iloc[:0][COLUMNS]
    year_gap = (pool["year"] - lot["year"]).abs().fillna(10) if pd.notna(lot.get("year")) else pd.Series(0, index=pool.index)
    flag_gap = (pool[DEFECT_FLAGS] != lot[DEFECT_FLAGS].to_numpy()).sum(axis=1)
    age_days = (at - pool["requestTimeBegin"]).dt.days
    rank = pd.DataFrame({"far": year_gap > MAX_YEAR_GAP, "year": year_gap, "flags": flag_gap, "age": age_days})
    rank = rank.sort_values(["far", "flags", "year", "age"])
    return pool.loc[rank.index[:n], COLUMNS]
