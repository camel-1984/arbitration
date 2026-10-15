import pandas as pd


def missing_shares(df: pd.DataFrame) -> pd.Series:
    shares = df.isna().mean().round(2)
    return shares[shares > 0].sort_values(ascending=False)


def share_table(df: pd.DataFrame, column: str) -> pd.DataFrame:
    counts = df[column].value_counts(dropna=False)
    return pd.DataFrame({"лотов": counts, "доля": (counts / len(df)).round(2)})


def price_summary(df: pd.DataFrame, by: str) -> pd.DataFrame:
    return (
        df.groupby(by)["sale_price"]
        .describe(percentiles=[0.25, 0.5, 0.75])[["count", "min", "25%", "50%", "75%", "max"]]
        .round(0)
    )


def period_summary(df: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "лотов": len(df),
        "первая публикация": df["requestTimeBegin"].min().date(),
        "последняя публикация": df["requestTimeBegin"].max().date(),
    })
