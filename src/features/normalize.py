import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.features.text import MODELS

TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t",
                     "u", "f", "h", "ts", "ch", "sh", "sch", "", "i", "", "e", "iu", "ia"]))
PHONETIC = [(r"([a-z])\1", r"\1"), ("ph", "f"), ("x", "ks"), ("q", "k"), ("w", "v"), ("j", "dzh"), (r"c(?=[eiy])", "s"),
            ("c", "k"), ("y", "i"), ("ee", "i"), ("oo", "u"), ("ou", "u")]
STOPWORDS = {"выпуска", "госномер", "регистрационный", "регистрационным", "кузов", "кузова", "null", "none", "без", "в",
             "с", "н", "и", "на", "по", "от", "идентификационный", "номер", "государственный", "гос", "рег", "двигатель",
             "шасси", "паспорт", "птс", "легковой", "легковая", "автомобиль", "марка", "модель", "тип", "категории",
             "категория", "год", "г", "vin", "цвет", "белый", "черный", "серый", "серебристый", "синий", "красный"}
ALIASES_PATH = Path("labels/model_aliases.csv")
MIN_LOTS = 5
LONG_NAME = 8
VIN_MIN_LOTS = 3
VIN_MIN_AGREEMENT = 0.8
VDS_PREFIX = 3
NO_FUZZY_MAKES = {"Mercedes-Benz", "BMW", "Lexus", "Infiniti"}
CODE_RE = re.compile(r"\d{4,}|[A-Z]{1,3}|(?=.*\d)(?=.*[A-Z])[A-Z0-9]{6,}")


def _translit(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", "".join(TRANSLIT.get(ch, ch) for ch in name.lower()))


def phonetic_key(name: str) -> str:
    s = _translit(name)
    for pattern, repl in PHONETIC:
        s = re.sub(pattern, repl, s)
    return s


def _canonical_spelling(lots: pd.DataFrame) -> pd.Series:
    key = lots["make"] + "|" + lots["model"].map(phonetic_key, na_action="ignore")
    def pick(names: pd.Series) -> str:
        counts = names.value_counts()
        latin = [n for n in counts.index if not re.search("[а-яё]", n.lower())]
        return latin[0] if latin else counts.index[0]
    top = lots["model"].groupby(key).agg(pick)
    return key.map(top).fillna(lots["model"])


def _edit_distance(a: str, b: str) -> int:
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, cb in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (ca != cb))
    return row[-1]


def _fuzzy_map(make: str, model: str, frequent: dict[str, list[str]]) -> str | None:
    candidates = {phonetic_key(m): m for m in frequent.get(make, [])}
    for canonical, aliases in MODELS.get(make, {}).items():
        candidates.update({phonetic_key(a): canonical for a in [canonical, *aliases]})
    key = phonetic_key(model)
    if key in candidates:
        return candidates[key]
    if make in NO_FUZZY_MAKES or any(ch.isdigit() for ch in key) or len(key) < 5:
        return None
    first = _translit(model)[:1]
    max_edits = 2 if len(key) >= LONG_NAME else 1
    pool = sorted((_edit_distance(key, k), k) for k in candidates
                  if _translit(candidates[k])[:1] == first and not any(ch.isdigit() for ch in k))
    return candidates[pool[0][1]] if pool and pool[0][0] <= max_edits else None


def _make_model(lots: pd.DataFrame) -> pd.Series:
    return lots["make"] + "|" + lots["model"]


def _lot_count(lots: pd.DataFrame, counts: pd.Series) -> pd.Series:
    return _make_model(lots).map(counts).fillna(0)


def _vin_table(lots: pd.DataFrame, by: list[str], target: str, fit: pd.Series) -> pd.Series:
    known = lots[fit & lots[target].notna() & lots[by].notna().all(axis=1)]
    stats = known.groupby(by)[target].agg(top=lambda s: s.value_counts().index[0], share=lambda s: s.value_counts(normalize=True).iloc[0],
                                          n="size")
    return stats[(stats["n"] >= VIN_MIN_LOTS) & (stats["share"] >= VIN_MIN_AGREEMENT)]["top"]


def _apply_aliases(lots: pd.DataFrame) -> pd.DataFrame:
    aliases = pd.read_csv(ALIASES_PATH, dtype=str, keep_default_na=False).set_index(["make", "model_raw"])
    key = pd.MultiIndex.from_arrays([lots["make"], lots["model"]])
    hit = key.isin(aliases.index)
    new = aliases.reindex(key[hit]).replace("", np.nan)
    lots.loc[hit, "make"] = new["make_new"].to_numpy()
    lots.loc[hit, "model"] = new["model_new"].to_numpy()
    return lots


def normalize_models(lots: pd.DataFrame, fit: pd.Series) -> pd.DataFrame:
    lots = _apply_aliases(lots.copy())
    lots["model"] = lots["model"].where(~lots["model"].str.lower().isin(STOPWORDS) & ~lots["model"].str.fullmatch("[а-яё]", na=False))
    lots["model"] = _canonical_spelling(lots)
    counts = _make_model(lots)[fit].value_counts()
    frequent = {}
    for key, n in counts.items():
        if n >= MIN_LOTS:
            make, name = key.split("|", 1)
            frequent.setdefault(make, []).append(name)
    source = pd.Series(np.where(lots["model"].notna(), "текст", "нет"), index=lots.index)
    rare = lots["model"].notna() & (_lot_count(lots, counts) < MIN_LOTS)
    mapped = {i: _fuzzy_map(lots.at[i, "make"], lots.at[i, "model"], frequent) for i in lots.index[rare]}
    mapped = pd.Series({i: m for i, m in mapped.items() if m and m != lots.at[i, "model"]}, dtype=object)
    lots.loc[mapped.index, "model"] = mapped
    source[mapped.index] = "словарь"

    lots["vds"] = lots["vin_vds"].str[:VDS_PREFIX]
    good = fit & _lot_count(lots, counts).ge(MIN_LOTS)
    wmi_make = _vin_table(lots, ["vin_wmi"], "make", fit)
    vin_make = lots["vin_wmi"].map(wmi_make)
    vin_model = pd.Series(list(zip(lots["vin_wmi"], lots["vds"])), index=lots.index).map(
        _vin_table(lots.assign(model=_make_model(lots)), ["vin_wmi", "vds"], "model", good))
    no_make = lots["make"].isna() & vin_make.notna()
    lots.loc[no_make, "make"] = vin_make[no_make]
    is_code = lots["model"].str.fullmatch(CODE_RE.pattern, na=False)
    still_rare = lots["model"].isna() | (is_code & ~lots["make"].isin(NO_FUZZY_MAKES) & (_lot_count(lots, counts) < MIN_LOTS))
    use_vin = still_rare & vin_model.notna() & (vin_model.str.split("|").str[0] == lots["make"])
    lots.loc[use_vin, "model"] = vin_model[use_vin].str.split("|", n=1).str[1]
    source[use_vin] = "VIN"
    return lots.drop(columns="vds").assign(model_source=source)
