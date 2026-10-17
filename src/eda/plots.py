import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")


def plot_price_distribution(df: pd.DataFrame) -> plt.Axes:
    ax = sns.histplot(data=df, x="sale_price", log_scale=True, bins=20)
    ax.set(xlabel="цена продажи, руб. (логарифмическая шкала)", ylabel="лотов")
    return ax


def plot_price_by_year(df: pd.DataFrame) -> plt.Axes:
    ax = sns.boxplot(data=df, x="year_published", y="sale_price", log_scale=True)
    ax.set(xlabel="год публикации торгов", ylabel="цена продажи, руб.")
    return ax


def plot_price_ratio(df: pd.DataFrame) -> plt.Axes:
    ax = sns.histplot(data=df, x="price_ratio", hue="tradeTypeDescription", bins=20, binrange=(0, 2), element="step")
    ax.axvline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="цена продажи / начальная цена этапа", ylabel="лотов")
    return ax


def plot_price_vs_age(df: pd.DataFrame) -> plt.Axes:
    known = df[df["age"].between(0, 40)]
    ax = sns.histplot(data=known, x="age", y="sale_price", log_scale=(False, True), discrete=(True, False), bins=(41, 40), cmap="Blues")
    medians = known.groupby("age")["sale_price"].median()
    ax.plot(medians.index, medians.values, color="black", linewidth=1.5, label="медиана")
    ax.set(xlabel="возраст машины на дату публикации, лет", ylabel="цена продажи, руб.")
    ax.legend()
    return ax


def plot_price_by_quarter(df: pd.DataFrame, min_lots: int = 100) -> plt.Axes:
    sizes = df["quarter"].value_counts()
    df = df[df["quarter"].isin(sizes[sizes >= min_lots].index)]
    q = df.groupby("quarter")["sale_price"].quantile([0.25, 0.5, 0.75]).unstack()
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.fill_between(q.index, q[0.25], q[0.75], alpha=0.25, label="P25-P75")
    ax.plot(q.index, q[0.5], marker="o", label="медиана")
    ax.set(xlabel="квартал публикации", ylabel="цена продажи, руб.")
    ax.legend()
    return ax
