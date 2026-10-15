import re

import pandas as pd

PATTERNS = {
    "год выпуска": r"(?:19[5-9]\d|20[0-3]\d)\s*(?:г\.?\s*в|г\.|года?\b)|год[а-я\s]*(?:выпуска|изготовления)\D{0,5}(?:19|20)\d\d",
    "пробег": r"пробег",
    "мощность": r"л\.\s*с\.|\bл/с\b|\bквт\b|мощност",
    "марка указана явно": r"марк[аи]\s*[:\-–]",
    "модель указана явно": r"модел[ьи]\s*[:\-–]",
    "VIN": r"\[VIN\]",
    "госномер": r"\[НОМЕР\]|г\.?\s*р\.?\s*з|гос\.?\s*номер|рег\.?\s*знак",
    "не на ходу / неисправен": r"не\s+на\s+ходу|неисправ|не\s+заводится|требует\s+ремонт",
    "ДТП / повреждения": r"дтп|поврежд|после\s+аварии|деформац|коррози",
    "залог": r"залог",
    "нет ключей / документов": r"(?:отсутству\w*|без|нет)\s+(?:ключ|птс|паспорт|документ|стс)",
    "местонахождение неизвестно": r"местонахождени\w*\s+(?:не\s*известно|неизвестно|не\s+установлено)",
    "арест / запрет": r"арест|запрет\s+на\s+регистрац",
}

MULTI_VEHICLE_RE = re.compile(r"лот\s*№?\s*\d+.*лот\s*№?\s*\d+|автомобили|транспортные средства:|сцепка", re.I | re.S)


def pattern_shares(texts: pd.Series) -> pd.DataFrame:
    texts = texts.fillna("")
    shares = {name: texts.str.contains(re.compile(pattern, re.I)).mean() for name, pattern in PATTERNS.items()}
    return pd.DataFrame({"доля лотов": shares}).sort_values("доля лотов", ascending=False).round(2)


def multi_vehicle_candidates(df: pd.DataFrame) -> pd.DataFrame:
    by_text = df["lot_info"].fillna("").str.contains(MULTI_VEHICLE_RE)
    by_vin = df["n_vins"] > 1
    return df.loc[by_text | by_vin, ["tradeId", "n_vins", "lot_info"]]
