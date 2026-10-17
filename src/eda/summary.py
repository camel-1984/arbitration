import numpy as np
import pandas as pd


def missing_features(df: pd.DataFrame) -> pd.Series:
    shares = df.isna().mean(axis=0)
    return shares[shares > 0].sort_values(ascending=False)


def count_feature(df: pd.DataFrame, column: str) -> pd.DataFrame:
    counts = df[column].value_counts(dropna=False)
    return pd.DataFrame({"лотов": counts, "доля": (counts / len(df)).round(2)})


def period_summary(df: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "лотов": len(df),
        "первая публикация": df["requestTimeBegin"].min().date(),
        "последняя публикация": df["requestTimeBegin"].max().date(),
    })


def strange_price(df: pd.DataFrame, x: float) -> pd.DataFrame:
    return df[df["price_ratio"] > x]


FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"]
LOT_COLUMNS = ["tradeId", "make", "model", "year", "stage", "lot_priceBegin", "sale_price", "price_ratio"]


def price_quantiles(df: pd.DataFrame) -> pd.Series:
    qs = [0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999]
    return df["sale_price"].quantile(qs).round(0).rename(index=lambda q: f"{q:.1%}")


def ratio_thresholds(df: pd.DataFrame, highs=(1.5, 2, 3, 5, 10), lows=(0.3, 0.2, 0.1, 0.05)) -> pd.DataFrame:
    rows = [(f"> {x}", len(strange_price(df, x))) for x in highs]
    rows += [(f"< {x}", int((df["price_ratio"] < x).sum())) for x in lows]
    return pd.DataFrame(rows, columns=["цена продажи / начальная цена этапа", "лотов"])


def extreme_lots(df: pd.DataFrame, column: str, n: int = 10, largest: bool = True) -> pd.DataFrame:
    picked = df.nlargest(n, column) if largest else df.nsmallest(n, column)
    return picked[LOT_COLUMNS].round({"price_ratio": 2})


def stage_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("stage").agg(
        лотов=("tradeId", "size"),
        медиана_цены=("sale_price", "median"),
        медиана_отношения=("price_ratio", "median"),
        один_участник=("allPartReqCount", lambda s: (s == 1).mean()),
    ).round(2)


def vin_duplicates(df: pd.DataFrame) -> pd.Series:
    dup = df[df["vin_hash"].notna() & df.duplicated("vin_hash", keep=False)].sort_values("requestTimeBegin")
    groups = dup.groupby("vin_hash")
    first, last = groups.first(), groups.last()
    gap = (last["requestTimeBegin"] - first["requestTimeBegin"]).dt.days
    relisted = (last["requestTimeBegin"] > first["salesContractTime"]).mean()
    return pd.Series({
        "групп": groups.ngroups,
        "лотов в группах": len(dup),
        "медиана дней между продажами": gap.median(),
        "один и тот же должник": (groups["debtor_key"].nunique() == 1).mean().round(2),
        "повтор после договора первой продажи": round(relisted, 2),
        "первая цена выше последней": (first["sale_price"] > last["sale_price"]).mean().round(2),
    })


def feature_coverage(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["make", "model", "year", "vin_year_code", "power_hp", "engine_cc", "lot_regionID"]
    filled = df[columns].notna().mean()
    flags = df[FLAGS].mean()
    return pd.concat([filled, flags]).round(3).to_frame("доля лотов")


def model_frequency(df: pd.DataFrame) -> pd.DataFrame:
    counts = (df["make"] + " " + df["model"]).value_counts()
    rows = []
    for low, high in [(1, 1), (2, 4), (5, 19), (20, None)]:
        mask = (counts >= low) & (counts <= high) if high else counts >= low
        rows.append((f"{low}-{high}" if high else f"{low}+", int(mask.sum()), round(counts[mask].sum() / len(df), 2)))
    return pd.DataFrame(rows, columns=["лотов на модель", "моделей", "доля лотов"])


def flag_effect(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for flag in FLAGS:
        on, off = df[df[flag] == 1], df[df[flag] == 0]
        if len(on) == 0:
            continue
        rows.append({
            "флаг": flag,
            "лотов": len(on),
            "цена с флагом / без": round(on["sale_price"].median() / off["sale_price"].median(), 2),
            "возраст с флагом": on["age"].median(),
            "возраст без флага": off["age"].median(),
        })
    return pd.DataFrame(rows).set_index("флаг")


def age_slope(df: pd.DataFrame) -> pd.Series:
    known = df[df["age"].between(0, 40)]
    slope, intercept = np.polyfit(known["age"], known["log_price"], 1)
    return pd.Series({
        "лотов с возрастом": len(known),
        "корреляция log цены и возраста": round(known[["age", "log_price"]].corr().iloc[0, 1], 2),
        "наклон log цены за год": round(slope, 3),
        "изменение цены за год": f"{np.exp(slope) - 1:.1%}",
    })


def quarter_summary(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("quarter").agg(
        лотов=("tradeId", "size"),
        медиана_цены=("sale_price", "median"),
        медиана_возраста=("age", "median"),
    )
