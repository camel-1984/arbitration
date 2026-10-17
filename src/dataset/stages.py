import numpy as np
import pandas as pd

from src.features.text import extract_make, extract_model

TRADES_PATH = "data/interim/cdtrf_trades.parquet"
CHAIN_MONTHS = 18
PUBLIC_OFFER_RATIO = 0.9


def _title_make_model(titles: pd.Series) -> pd.DataFrame:
    titles = titles.fillna("")
    makes = titles.map(extract_make)
    models = [extract_model([t], m) for t, m in zip(titles, makes)]
    return pd.DataFrame({"title_make": makes, "title_model": models}, index=titles.index)


def add_first_price(lots: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    auctions = trades[(trades["tradeType"] == "Аукцион") & trades["price"].gt(0) & trades["debtor_name_key"].notna()]
    own = pd.concat([lots[["tradeId", "debtor_name_key", "title_key", "vin_hash", "requestTimeBegin"]],
                     _title_make_model(lots["lot_title"])], axis=1)
    pairs = own.merge(auctions, on="debtor_name_key", suffixes=("", "_a"))
    earlier = (pairs["requestTimeBegin_a"] <= pairs["requestTimeBegin"]) & (
        pairs["requestTimeBegin_a"] >= pairs["requestTimeBegin"] - pd.DateOffset(months=CHAIN_MONTHS))
    same_title = pairs["title_key"] == pairs["title_key_a"]
    same_vin = pairs["vin_hash"].notna() & (pairs["vin_hash"] == pairs["title_vin_hash"])
    same_model = pairs["title_make"].notna() & pairs["title_model"].notna() & (pairs["title_make"] == pairs["title_make_a"]) & (
        pairs["title_model"] == pairs["title_model_a"])
    pairs["level"] = np.select([same_title | same_vin, same_model], ["название или VIN", "марка и модель"], "")
    chain = pairs[earlier & (pairs["level"] != "")].sort_values("requestTimeBegin_a")
    first = chain.groupby("tradeId").first()
    is_public = ~lots["tradeTypeDescription"].str.contains("аукцион|конкурс")
    fallback = lots["lot_priceBegin"] / np.where(is_public, PUBLIC_OFFER_RATIO, 1)
    linked = lots["tradeId"].map(first["price"])
    source = lots["tradeId"].map(first["level"]).fillna(pd.Series(np.where(is_public, "правило 0.9", "своя цена"), index=lots.index))
    first_date = lots["tradeId"].map(first["requestTimeBegin_a"]).where(source != "своя цена", lots["requestTimeBegin"])
    return lots.assign(first_price=linked.fillna(fallback), first_price_source=source, first_date=first_date)


def first_auctions(trades: pd.DataFrame) -> pd.DataFrame:
    auctions = trades[(trades["tradeType"] == "Аукцион") & trades["price"].gt(0) & trades["debtor_name_key"].notna()
                      & (trades["categories"] == ",1,")]
    cols = ["tradeId", "debtor_name_key", "title_key", "title_vin_hash", "title_make", "title_model", "requestTimeBegin"]
    pairs = auctions[cols].merge(auctions[cols], on="debtor_name_key", suffixes=("", "_e"))
    earlier = (pairs["requestTimeBegin_e"] < pairs["requestTimeBegin"]) & (
        pairs["requestTimeBegin_e"] >= pairs["requestTimeBegin"] - pd.DateOffset(months=CHAIN_MONTHS))
    same_car = (pairs["title_key"] == pairs["title_key_e"]) | (
        pairs["title_vin_hash"].notna() & (pairs["title_vin_hash"] == pairs["title_vin_hash_e"])) | (
        pairs["title_make"].notna() & pairs["title_model"].notna() & (pairs["title_make"] == pairs["title_make_e"])
        & (pairs["title_model"] == pairs["title_model_e"]))
    repeated = set(pairs.loc[earlier & same_car, "tradeId"])
    return auctions[~auctions["tradeId"].isin(repeated)].assign(sold_first=lambda a: a["status"] == "Подписан договор")
