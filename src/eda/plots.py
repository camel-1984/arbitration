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
