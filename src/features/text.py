import re

import pandas as pd

MAKES = {
    "Lada": ["lada", "лада", "ваз", "vaz"],
    "GAZ": ["газ", "gaz"],
    "UAZ": ["уаз", "uaz"],
    "Kia": ["kia", "киа"],
    "Hyundai": ["hyundai", "hyndai", "хендай", "хендэ", "хёндай", "хенде", "хёнде", "хундай", "хэндай"],
    "Renault": ["renault", "рено"],
    "Toyota": ["toyota", "тойота"],
    "Lexus": ["lexus", "лексус"],
    "Nissan": ["nissan", "ниссан", "нисан"],
    "Volkswagen": ["volkswagen", "фольксваген", "vw"],
    "Skoda": ["skoda", "škoda", "шкода"],
    "Audi": ["audi", "ауди"],
    "BMW": ["bmw", "бмв"],
    "Mercedes-Benz": ["mercedes-benz", "mercedes benz", "mercedes", "мерседес-бенц", "мерседес бенц", "мерседес"],
    "Opel": ["opel", "опель"],
    "Ford": ["ford", "форд"],
    "Chevrolet": ["chevrolet", "шевроле"],
    "Daewoo": ["daewoo", "дэу", "деу"],
    "Mitsubishi": ["mitsubishi", "мицубиси", "митсубиси", "мицубиши"],
    "Mazda": ["mazda", "мазда"],
    "Honda": ["honda", "хонда"],
    "Subaru": ["subaru", "субару"],
    "Suzuki": ["suzuki", "сузуки", "судзуки"],
    "Volvo": ["volvo", "вольво"],
    "Peugeot": ["peugeot", "пежо"],
    "Citroen": ["citroen", "citroën", "ситроен"],
    "Chery": ["chery", "чери"],
    "Geely": ["geely", "джили"],
    "Haval": ["haval", "хавал", "хавейл"],
    "Great Wall": ["great wall", "грейт вол", "грейт волл"],
    "Exeed": ["exeed", "эксид"],
    "Jetour": ["jetour", "джетур"],
    "Changan": ["changan", "чанган"],
    "Omoda": ["omoda", "омода"],
    "Zotye": ["zotye", "зоти"],
    "Lifan": ["lifan", "лифан"],
    "SsangYong": ["ssangyong", "ssang yong", "санг енг", "саньенг", "ссангйонг"],
    "Acura": ["acura", "акура"],
    "Infiniti": ["infiniti", "инфинити"],
    "Land Rover": ["land rover", "range rover", "ленд ровер", "рендж ровер"],
    "Porsche": ["porsche", "порше"],
    "Jeep": ["jeep", "джип"],
    "Datsun": ["datsun", "датсун"],
}

MODELS = {
    "Lada": {"Granta": ["granta", "гранта"], "Kalina": ["kalina", "калина"], "Priora": ["priora", "приора"],
             "Vesta": ["vesta", "веста"], "Largus": ["largus", "ларгус"], "XRAY": ["xray", "x-ray", "иксрей"],
             "4x4": ["4x4", "4х4", "нива", "niva legend", "niva"]},
    "Kia": {"Rio": ["rio", "рио"], "Ceed": ["ceed", "cee'd", "cee*d", "сид"], "Cerato": ["cerato", "церато"],
            "Sportage": ["sportage", "спортейдж"], "Picanto": ["picanto", "пиканто"], "Sorento": ["sorento", "соренто"],
            "Optima": ["optima", "оптима"], "Soul": ["soul", "соул"]},
    "Hyundai": {"Solaris": ["solaris", "солярис"], "Accent": ["accent", "акцент"], "Getz": ["getz", "гетц"],
                "ix35": ["ix35", "ix 35"], "Tucson": ["tucson", "туссан"], "Sonata": ["sonata", "соната"],
                "Elantra": ["elantra", "элантра"], "Creta": ["creta", "крета"], "Santa Fe": ["santa fe", "санта фе"],
                "Veloster": ["veloster", "велостер"], "Verna": ["verna", "верна"]},
    "Renault": {"Logan": ["logan", "логан"], "Sandero": ["sandero", "сандеро"], "Duster": ["duster", "дастер"],
                "Kaptur": ["kaptur", "каптур"], "Arkana": ["arkana", "аркана"], "Megane": ["megane", "меган"],
                "Fluence": ["fluence", "флюенс"], "Symbol": ["symbol", "симбол"]},
    "Toyota": {"Corolla": ["corolla", "королла"], "Camry": ["camry", "камри"], "RAV4": ["rav4", "rav 4", "рав 4", "рав4"],
               "Land Cruiser": ["land cruiser", "ленд крузер"], "Avensis": ["avensis", "авенсис"],
               "Auris": ["auris", "аурис"], "Harrier": ["harrier", "харриер"], "Fortuner": ["fortuner", "фортунер"],
               "Estima": ["estima", "эстима"], "Sienna": ["sienna", "сиенна"], "Prius": ["prius", "приус"]},
    "Volkswagen": {"Polo": ["polo", "поло"], "Jetta": ["jetta", "джетта"], "Passat": ["passat", "пассат"],
                   "Tiguan": ["tiguan", "тигуан"], "Golf": ["golf", "гольф"], "Touareg": ["touareg", "туарег"]},
    "Skoda": {"Rapid": ["rapid", "рапид"], "Octavia": ["octavia", "октавия"], "Fabia": ["fabia", "фабия"],
              "Yeti": ["yeti", "йети"], "Kodiaq": ["kodiaq", "кодиак"]},
    "Ford": {"Focus": ["focus", "фокус", "fokus"], "Fiesta": ["fiesta", "фиеста"], "Mondeo": ["mondeo", "мондео"],
             "Kuga": ["kuga", "куга"], "Explorer": ["explorer", "эксплорер"], "Fusion": ["fusion", "фьюжн"]},
    "Chevrolet": {"Lacetti": ["lacetti", "лачетти", "klan", "клан"], "Cruze": ["cruze", "круз"],
                  "Aveo": ["aveo", "авео"], "Niva": ["niva", "нива"], "Orlando": ["orlando", "орландо"],
                  "Cobalt": ["cobalt", "кобальт"], "Lanos": ["lanos", "ланос"]},
    "Opel": {"Astra": ["astra", "астра"], "Corsa": ["corsa", "корса"], "Zafira": ["zafira", "зафира"],
             "Vectra": ["vectra", "вектра"], "Insignia": ["insignia", "инсигния"]},
    "Nissan": {"Almera": ["almera", "альмера"], "Qashqai": ["qashqai", "кашкай"], "X-Trail": ["x-trail", "икс-трейл"],
               "Tiida": ["tiida", "тиида"], "Note": ["note", "ноут"], "Sentra": ["sentra", "сентра"],
               "Teana": ["teana", "теана"], "Sunny": ["sunny", "санни"], "Juke": ["juke", "жук"]},
    "Mitsubishi": {"Lancer": ["lancer", "лансер"], "Outlander": ["outlander", "аутлендер"], "ASX": ["asx"],
                   "Pajero": ["pajero", "паджеро"], "L200": ["l200", "l-200", "л200"]},
    "Mazda": {"3": ["mazda 3", "mazda3", "мазда 3"], "6": ["mazda 6", "mazda6", "мазда 6"], "CX-5": ["cx-5", "cx5"],
              "Demio": ["demio", "демио"], "Familia": ["familia", "фамилия"], "Premacy": ["premacy", "премаси"]},
    "Honda": {"Civic": ["civic", "цивик"], "Accord": ["accord", "аккорд"], "CR-V": ["cr-v", "crv"], "Fit": ["fit", "фит"]},
    "Daewoo": {"Nexia": ["nexia", "нексия"], "Matiz": ["matiz", "матиз"], "Gentra": ["gentra", "джентра"]},
    "Geely": {"Coolray": ["coolray", "кулрей"], "Atlas": ["atlas", "атлас"], "Emgrand": ["emgrand", "эмгранд"]},
    "Chery": {"Tiggo 7 Pro": ["tiggo 7 pro"], "Tiggo 4": ["tiggo 4"], "Tiggo 8": ["tiggo 8"], "Tiggo": ["tiggo", "тигго"]},
    "Audi": {"A4": ["a4", "а4"], "A6": ["a6", "а6"], "Q5": ["q5"], "Q7": ["q7"], "A3": ["a3", "а3"]},
    "UAZ": {"Patriot": ["patriot", "патриот"], "Hunter": ["hunter", "хантер"]},
    "Suzuki": {"SX4": ["sx4", "сх4"], "Grand Vitara": ["grand vitara", "гранд витара"]},
}

LADA_CODES = {"1117": "Kalina", "1118": "Kalina", "1119": "Kalina", "2170": "Priora", "2171": "Priora", "2172": "Priora",
              "2190": "Granta", "2191": "Granta", "2192": "Granta", "2194": "Granta", "2180": "Vesta", "2181": "Vesta",
              "RS0": "Largus", "KS0": "Largus", "GAB": "XRAY", "GFK": "Vesta", "GFL": "Vesta"}
MODEL_STOPWORDS = {"модель", "модели", "марка", "марки", "автомобиль", "легковой", "года", "г", "vin"}
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

YEAR_RES = [
    re.compile(r"год\w*\s*(?:выпуска|изготовления|производства)\D{0,20}((?:19|20)\d\d)", re.I),
    re.compile(r"\b((?:19|20)\d\d)\s*,?\s*(?:г\.?\s*в|г/в|гв\b|года?\b|г\.)", re.I),
]
POWER_RES = [
    (re.compile(r"кВт\s*/\s*л\.?\s*с\.?\)?\s*:?\s*(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)", re.I), 2),
    (re.compile(r"л\.?\s*с\.?\s*\(\s*кВт\s*\)\s*:?\s*(\d+(?:[.,]\d+)?)\s*\(\s*(\d+(?:[.,]\d+)?)", re.I), 1),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*л\.?\s*с", re.I), 1),
]
VOLUME_RES = [
    re.compile(r"(?:рабочий\s+)?объ[её]м\w*(?:\s+двигателя)?\D{0,25}(\d+(?:[.,]\d+)?)", re.I),
    re.compile(r"(\d{3,4}(?:[.,]\d+)?)\s*(?:куб|см3|см³)", re.I),
]

NEGATION = r"(?<!нет\s)(?<!без\s)"
FLAG_PATTERNS = {
    "major_defect": r"не\s+на\s+ходу|не\s+заводится|не\s+эксплуатир|(?:тс|автомобиль|транспортное средство)\s+неисправ"
                    r"|неисправн\w*\s+(?:двигател|акпп|кпп|коробк)|капитальн\w*\s+ремонт"
                    r"|(?:ремонт|замен\w*)\s+(?:двигател|акпп|кпп|коробк)|порван\w*\s+ремень",
    "damaged": NEGATION + r"(?:дтп|после\s+аварии|деформац|коррози|вмятин|разбит|поврежден\w*\s+(?:кузов|двер|бампер|крыл|крыш|кап)"
               r"|повреждения\s+(?:кузова|лкп)|дефект\w*\s+(?:по\s+)?кузов|замен\w*\s+(?:капота|бампера|двер|крыл|лобового))",
    "no_keys_or_docs": r"(?:отсутству\w*|без|нет|утерян\w*)\s+(?:ключ|птс|паспорт|стс|свидетельств|документ)"
                       r"|(?:ключ\w*|птс|стс)\s+(?:отсутству|нет|утерян)",
    "pledge": r"залог",
    "arrest_or_ban": r"арест|запрет\w*\s+на\s+регистрац|наложенных\s+ограничений|имеет\s+обременения,\s+ограничения",
    "location_unknown": r"местонахождени\w*\s+(?:не\s*известно|неизвестно|не\s+установлено)|не\s+передан\w*\s+(?:финансовому\s+)?управляющ"
                        r"|уклоняется\s+от\s+передачи|в\s+розыске|осмотр\s+(?:невозможен|не\s+производился)",
}


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _alias_regex(alias: str) -> re.Pattern:
    return re.compile(r"(?<![a-zа-яё0-9])" + re.escape(alias) + r"(?![a-zа-яё])", re.I)


def _alias_patterns(names: dict[str, list[str]]) -> list[tuple[str, re.Pattern]]:
    pairs = sorted(((name, alias) for name, aliases in names.items() for alias in aliases), key=lambda x: -len(x[1]))
    return [(name, _alias_regex(alias)) for name, alias in pairs]


MAKE_ALIASES = _alias_patterns(MAKES)
MODEL_ALIASES = {make: _alias_patterns(models) for make, models in MODELS.items()}


def extract_make(text: str) -> str | None:
    hits = [(m.start(), make) for make, pattern in MAKE_ALIASES if (m := pattern.search(text))]
    return min(hits)[1] if hits else None


def _lada_from_code(text: str) -> str | None:
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z]{2,3}\d{3}|\d{4,6})(?![A-Za-z0-9])", text, re.I):
        code = m.group(1).upper()
        for prefix, model in LADA_CODES.items():
            if code.startswith(prefix):
                return model
        if code.isdigit() and code.startswith("21"):
            return code[:4]
    return None


def extract_model(text: str, make: str | None) -> str | None:
    if make is None:
        return None
    hits = [(m.start(), model) for model, pattern in MODEL_ALIASES.get(make, []) if (m := pattern.search(text))]
    if hits:
        return min(hits)[1]
    if make == "Lada" and (model := _lada_from_code(text)):
        return model
    make_matches = [m for name, pattern in MAKE_ALIASES if name == make and (m := pattern.search(text))]
    if not make_matches:
        return None
    end = min(make_matches, key=lambda m: m.start()).end()
    for token in TOKEN_RE.findall(text[end:end + 40]):
        if token.lower() not in MODEL_STOPWORDS and not re.fullmatch(r"(19|20)\d\d", token):
            return token
    return None


def extract_year(text: str) -> int | None:
    for pattern in YEAR_RES:
        if m := pattern.search(text):
            return int(m.group(1))
    return None


def extract_power_hp(text: str) -> float | None:
    for pattern, group in POWER_RES:
        if m := pattern.search(text):
            value = _to_float(m.group(group))
            if 30 <= value <= 800:
                return value
    return None


def extract_engine_cc(text: str) -> float | None:
    for pattern in VOLUME_RES:
        for m in pattern.finditer(text):
            value = _to_float(m.group(1))
            if value < 10:
                value *= 1000
            if 600 <= value <= 8000:
                return round(value)
    return None


def extract_flags(text: str) -> dict[str, int]:
    return {name: int(bool(re.search(pattern, text, re.I))) for name, pattern in FLAG_PATTERNS.items()}


def extract_features(title: str | None, info: str | None) -> dict:
    info = info or ""
    text = f"{title or ''} {info}"
    make = extract_make(text)
    return {
        "make": make,
        "model": extract_model(text, make),
        "year": extract_year(text),
        "power_hp": extract_power_hp(info),
        "engine_cc": extract_engine_cc(info),
        **extract_flags(text),
    }


def extract_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = [extract_features(title, info) for title, info in zip(df["lot_title"], df["lot_info"])]
    return pd.DataFrame(rows, index=df.index)
