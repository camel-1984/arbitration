import numpy as np
import pandas as pd

from src.models import linear

GROUPS = {
    "cat__make_": "марка и модель", "cat__make_model_": "марка и модель", "cat__region_": "регион", "cat__debtType_": "тип должника",
    "age__": "возраст", "num__log_power": "мощность", "num__log_engine": "объём двигателя", "months__": "дата публикации",
    "num__log_first_price": "начальная цена", "num__missingindicator_log_power": "мощность", "num__missingindicator_log_engine": "объём двигателя",
    "num__missingindicator_log_first_price": "начальная цена", "flags__": "",
}


def _group(name: str) -> str:
    for prefix, group in sorted(GROUPS.items(), key=lambda kv: -len(kv[0])):
        if name.startswith(prefix):
            return group or name.removeprefix(prefix)
    return name


def fit(train: pd.DataFrame, with_start: bool = False):
    return linear.make_model(0.5, with_start=with_start).fit(linear.features(train), train["log_price"])


def contributions(model, lots: pd.DataFrame) -> pd.DataFrame:
    preprocess, regressor = model.steps[0][1], model.steps[-1][1]
    names = [_group(n) for n in preprocess.get_feature_names_out()]
    x = linear.features(lots)
    matrix = preprocess.transform(x)
    dense = matrix.toarray() if hasattr(matrix, "toarray") else matrix
    return pd.DataFrame(dense * regressor.coef_, columns=names, index=x.index).T.groupby(level=0).sum().T


def factors(model, train: pd.DataFrame, lots: pd.DataFrame) -> pd.DataFrame:
    return np.exp(contributions(model, lots) - contributions(model, train).mean()) - 1
