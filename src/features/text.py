import re

import pandas as pd

MAKES = {
    "Lada": ["lada", "лада", "ваз", "vaz"],
    "GAZ": ["газ", "gaz"],
    "UAZ": ["уаз", "uaz"],
    "Moskvich": ["москвич", "moskvich"],
    "Kia": ["kia", "киа"],
    "Hyundai": ["hyundai", "hyndai", "хендай", "хендэ", "хёндай", "хенде", "хёнде", "хундай", "хэндай", "хюндай"],
    "Renault": ["renault", "рено"],
    "Toyota": ["toyota", "тойота"],
    "Lexus": ["lexus", "лексус"],
    "Nissan": ["nissan", "ниссан", "нисан"],
    "Infiniti": ["infiniti", "инфинити"],
    "Datsun": ["datsun", "датсун"],
    "Volkswagen": ["volkswagen", "фольксваген", "фольцваген", "vw"],
    "Skoda": ["skoda", "škoda", "шкода"],
    "Audi": ["audi", "ауди"],
    "BMW": ["bmw", "бмв"],
    "Mercedes-Benz": ["mercedes-benz", "mercedes benz", "mercedes", "мерседес-бенц", "мерседес бенц", "мерседес"],
    "Porsche": ["porsche", "порше"],
    "Opel": ["opel", "опель"],
    "Ford": ["ford", "форд"],
    "Chevrolet": ["chevrolet", "шевроле", "шеврале"],
    "Daewoo": ["daewoo", "дэу", "деу", "дэо"],
    "Ravon": ["ravon", "равон"],
    "Mitsubishi": ["mitsubishi", "мицубиси", "митсубиси", "мицубиши", "митсубиши"],
    "Mazda": ["mazda", "мазда"],
    "Honda": ["honda", "хонда"],
    "Acura": ["acura", "акура"],
    "Subaru": ["subaru", "субару"],
    "Suzuki": ["suzuki", "сузуки", "судзуки"],
    "Daihatsu": ["daihatsu", "дайхатсу", "дайхацу"],
    "Volvo": ["volvo", "вольво"],
    "Peugeot": ["peugeot", "пежо"],
    "Citroen": ["citroen", "citroën", "ситроен", "ситроэн"],
    "Fiat": ["fiat", "фиат"],
    "Jaguar": ["jaguar", "ягуар"],
    "Land Rover": ["land rover", "range rover", "ленд ровер", "лэнд ровер", "рендж ровер", "ленд-ровер"],
    "Mini": ["mini cooper", "mini"],
    "Jeep": ["jeep", "джип"],
    "Dodge": ["dodge", "додж"],
    "Chrysler": ["chrysler", "крайслер"],
    "Cadillac": ["cadillac", "кадиллак"],
    "Pontiac": ["pontiac", "понтиак"],
    "SsangYong": ["ssangyong", "ssang yong", "санг енг", "саньенг", "ссангйонг", "ссанг йонг", "сангйонг"],
    "Chery": ["chery", "чери"],
    "Geely": ["geely", "джили"],
    "Haval": ["haval", "хавал", "хавейл"],
    "Great Wall": ["great wall", "грейт вол", "грейт волл"],
    "Tank": ["tank"],
    "Exeed": ["exeed", "эксид"],
    "Omoda": ["omoda", "омода"],
    "Jaecoo": ["jaecoo", "джейку"],
    "Jetour": ["jetour", "джетур"],
    "Changan": ["changan", "чанган"],
    "BAIC": ["baic", "баик"],
    "FAW": ["faw", "фав"],
    "JAC": ["jac", "джак"],
    "Dongfeng": ["dongfeng", "донгфенг", "dong feng"],
    "Kaiyi": ["kaiyi", "кайи"],
    "Livan": ["livan", "ливан"],
    "Zotye": ["zotye", "зоти"],
    "Lifan": ["lifan", "лифан"],
    "Vortex": ["vortex", "вортекс"],
    "Brilliance": ["brilliance"],
    "BYD": ["byd"],
    "Tesla": ["tesla", "тесла"],
    "Seat": ["seat"],
    "Smart": ["smart"],
    "MAZ": ["маз", "maz"],
    "KAMAZ": ["камаз", "kamaz"],
}

MODELS = {
    "Lada": {"Granta": ["granta", "гранта"], "Kalina": ["kalina", "калина"], "Priora": ["priora", "приора"],
             "Vesta": ["vesta", "веста"], "Largus": ["largus", "ларгус"], "XRAY": ["xray", "x-ray", "иксрей"],
             "4x4": ["4x4", "4х4", "нива", "niva legend", "niva"], "Oka": ["ока", "oka"]},
    "Kia": {"Rio": ["rio", "рио"], "Ceed": ["ceed", "cee'd", "cee*d", "сид", "jd"], "Cerato": ["cerato", "церато", "серато"],
            "Sportage": ["sportage", "спортейдж", "спортэйдж"], "Picanto": ["picanto", "пиканто"],
            "Sorento": ["sorento", "соренто"], "Optima": ["optima", "оптима"], "Soul": ["soul", "соул"],
            "Spectra": ["spectra", "спектра"], "Carens": ["carens", "каренс"], "Venga": ["venga", "венга"],
            "K5": ["k5"], "Seltos": ["seltos", "селтос"], "Mohave": ["mohave", "мохав"], "Carnival": ["carnival", "карнивал"],
            "Magentis": ["magentis", "маджентис"], "K900": ["k900"], "Quoris": ["quoris"]},
    "Hyundai": {"Solaris": ["solaris", "солярис"], "Accent": ["accent", "акцент"], "Getz": ["getz", "гетц"],
                "ix35": ["ix35", "ix 35"], "Tucson": ["tucson", "туссан", "тусан"], "Sonata": ["sonata", "соната"],
                "Elantra": ["elantra", "элантра"], "Creta": ["creta", "крета"], "Santa Fe": ["santa fe", "санта фе"],
                "Veloster": ["veloster", "велостер"], "Verna": ["verna", "верна"], "i30": ["i30"], "i20": ["i20"],
                "i40": ["i40"], "Matrix": ["matrix", "матрикс"], "Starex": ["starex", "старекс"],
                "Grand Starex": ["grand starex", "h-1", "h1"], "Equus": ["equus"], "Genesis": ["genesis", "генезис"]},
    "Renault": {"Logan": ["logan", "логан", "sr"], "Sandero": ["sandero", "сандеро"], "Duster": ["duster", "дастер"],
                "Kaptur": ["kaptur", "каптур"], "Arkana": ["arkana", "аркана"], "Megane": ["megane", "меган", "megan"],
                "Fluence": ["fluence", "флюенс"], "Symbol": ["symbol", "симбол"], "Laguna": ["laguna", "лагуна"],
                "Scenic": ["scenic", "сценик"], "Clio": ["clio", "клио"], "Koleos": ["koleos", "колеос"],
                "Logan Stepway": ["logan stepway"], "Sandero Stepway": ["sandero stepway"], "Dokker": ["dokker", "доккер"], "Kangoo": ["kangoo", "кангу"]},
    "Toyota": {"Corolla": ["corolla", "королла", "corola"], "Camry": ["camry", "камри"],
               "RAV4": ["rav4", "rav 4", "рав 4", "рав4"], "Land Cruiser": ["land cruiser", "ленд крузер"],
               "Land Cruiser Prado": ["land cruiser prado", "ленд крузер прадо", "prado", "прадо"],
               "Avensis": ["avensis", "авенсис"], "Auris": ["auris", "аурис"], "Harrier": ["harrier", "харриер"],
               "Fortuner": ["fortuner", "фортунер"], "Estima": ["estima", "эстима"], "Sienna": ["sienna", "сиенна"],
               "Prius": ["prius", "приус"], "Corolla Fielder": ["corolla fielder", "corola fielder", "fielder", "филдер"],
               "Corolla Levin": ["corolla levin"], "Corona Premio": ["corona premio"], "Premio": ["premio", "премио"],
               "Allion": ["allion", "аллион"], "Vitz": ["vitz", "витц"], "Belta": ["belta"], "Sienta": ["sienta"],
               "Carina": ["carina", "карина"], "Starlet": ["starlet", "старлет"], "Duet": ["duet"],
               "Platz": ["platz", "платц"], "Highlander": ["highlander", "хайлендер"], "Hilux": ["hilux", "хайлюкс"],
               "Wish": ["wish"], "Mark II": ["mark ii", "mark 2", "марк 2"], "Crown": ["crown", "краун"],
               "HiAce": ["hiace", "хайс"], "Noah": ["noah"], "Voxy": ["voxy"], "Ipsum": ["ipsum"], "Funcargo": ["funcargo"], "Vista": ["vista", "виста"], "Caldina": ["caldina", "калдина"],
               "Sprinter": ["sprinter", "спринтер"], "Raum": ["raum"], "Probox": ["probox"], "Passo": ["passo"],
               "Lite Ace": ["lite ace", "liteace"], "Town Ace": ["town ace", "townace"]},
    "Volkswagen": {"Polo": ["polo", "поло"], "Jetta": ["jetta", "джетта"], "Passat": ["passat", "пассат"],
                   "Passat CC": ["passat cc"], "Tiguan": ["tiguan", "тигуан"], "Golf": ["golf", "гольф"],
                   "Touareg": ["touareg", "туарег"], "Multivan": ["multivan", "мультивен"], "Caddy": ["caddy", "кадди"],
                   "Transporter": ["transporter", "транспортер"], "Touran": ["touran", "туран"], "Bora": ["bora"],
                   "Teramont": ["teramont", "терамонт"], "Taos": ["taos"], "Amarok": ["amarok"], "Sharan": ["sharan", "шаран"]},
    "Skoda": {"Rapid": ["rapid", "рапид"], "Octavia": ["octavia", "октавия", "октавиа"], "Fabia": ["fabia", "фабия"],
              "Yeti": ["yeti", "йети"], "Kodiaq": ["kodiaq", "кодиак"], "Superb": ["superb", "суперб"],
              "Karoq": ["karoq", "карок"], "Roomster": ["roomster"]},
    "Ford": {"Focus": ["focus", "фокус", "fokus"], "Fiesta": ["fiesta", "фиеста"], "Mondeo": ["mondeo", "мондео"],
             "Kuga": ["kuga", "куга"], "Explorer": ["explorer", "эксплорер"], "Fusion": ["fusion", "фьюжн"],
             "C-Max": ["c-max", "с-макс", "focus c-max"], "S-Max": ["s-max"], "Galaxy": ["galaxy"],
             "EcoSport": ["ecosport", "экоспорт"], "Ka": ["ka", "ка"], "Escape": ["escape"], "Transit": ["transit", "транзит"]},
    "Chevrolet": {"Lacetti": ["lacetti", "лачетти", "klan", "клан"], "Cruze": ["cruze", "круз"],
                  "Aveo": ["aveo", "авео"], "Niva": ["niva", "нива"], "Orlando": ["orlando", "орландо"],
                  "Cobalt": ["cobalt", "кобальт"], "Lanos": ["lanos", "ланос"], "Captiva": ["captiva", "каптива", "klac", "клас"],
                  "Spark": ["spark", "спарк"], "Epica": ["epica", "эпика"], "Optra": ["optra", "оптра"],
                  "Tahoe": ["tahoe", "тахо"], "TrailBlazer": ["trailblazer"], "Rezzo": ["rezzo", "реззо"], "Malibu": ["malibu"]},
    "Opel": {"Astra": ["astra", "астра"], "Corsa": ["corsa", "корса"], "Zafira": ["zafira", "зафира"],
             "Vectra": ["vectra", "вектра"], "Insignia": ["insignia", "инсигния"], "Meriva": ["meriva", "мерива"],
             "Mokka": ["mokka", "мокка"], "Antara": ["antara", "антара"], "Kadett": ["kadett", "кадет", "кадетт"],
             "Omega": ["omega", "омега"], "Frontera": ["frontera"]},
    "Nissan": {"Almera": ["almera", "альмера"], "Almera Classic": ["almera classic", "альмера классик"],
               "Qashqai": ["qashqai", "кашкай"], "X-Trail": ["x-trail", "икс-трейл", "х-трейл"],
               "Tiida": ["tiida", "тиида"], "Note": ["note", "ноут", "ноте"], "Sentra": ["sentra", "сентра"],
               "Teana": ["teana", "теана"], "Sunny": ["sunny", "санни"], "Juke": ["juke", "жук"],
               "Primera": ["primera", "примера", "премьера"], "Micra": ["micra", "микра"], "Murano": ["murano", "мурано"],
               "Pathfinder": ["pathfinder", "патфайндер"], "Terrano": ["terrano", "террано"], "Wingroad": ["wingroad", "вингроуд", "вингроад"],
               "AD": ["ad"], "Bluebird Sylphy": ["bluebird sylphy", "sylphy"], "Bluebird": ["bluebird", "блюберд"],
               "Cube": ["cube"], "Serena": ["serena"], "Presage": ["presage", "пресаж"], "Prairie Joy": ["prairie joy", "прерия джой"],
               "Prairie": ["prairie", "прерия"], "Dayz Roox": ["dayz roox"], "Dayz": ["dayz"], "Leaf": ["leaf", "лиф"],
               "March": ["march"], "Patrol": ["patrol", "патрол"], "Navara": ["navara"], "Laurel": ["laurel"]},
    "Mitsubishi": {"Lancer": ["lancer", "лансер"], "Lancer Cedia": ["lancer cedia", "cedia"],
                   "Outlander": ["outlander", "аутлендер"], "ASX": ["asx"], "Pajero": ["pajero", "паджеро"],
                   "Pajero Sport": ["pajero sport"], "L200": ["l200", "l-200", "л200"], "Colt": ["colt", "кольт"],
                   "Galant": ["galant", "галант"], "Carisma": ["carisma"], "Grandis": ["grandis"], "Delica": ["delica"]},
    "Mazda": {"3": ["mazda 3", "mazda3", "мазда 3"], "6": ["mazda 6", "mazda6", "мазда 6"], "CX-5": ["cx-5", "cx5"],
              "CX-7": ["cx-7"], "CX-9": ["cx-9"], "Demio": ["demio", "демио"], "Familia": ["familia", "фамилия"],
              "Premacy": ["premacy", "премаси"], "Tribute": ["tribute"], "Axela": ["axela"], "Atenza": ["atenza"],
              "MPV": ["mpv"], "Capella": ["capella"], "Bongo": ["bongo"]},
    "Honda": {"Civic": ["civic", "цивик"], "Civic Ferio": ["civic ferio", "цивик ферио"], "Accord": ["accord", "аккорд"],
              "CR-V": ["cr-v", "crv", "цр-в"], "Fit": ["fit", "фит"], "Freed": ["freed"], "Airwave": ["airwave"],
              "Stepwgn": ["stepwgn", "step wgn"], "Odyssey": ["odyssey"], "Edix": ["edix"], "Mobilio": ["mobilio"],
              "Stream": ["stream"], "Partner": ["partner"], "Pilot": ["pilot"], "Jazz": ["jazz"], "HR-V": ["hr-v"]},
    "Daewoo": {"Nexia": ["nexia", "нексия", "нексиа"], "Matiz": ["matiz", "матиз"], "Gentra": ["gentra", "джентра"],
               "Espero": ["espero"]},
    "Geely": {"Coolray": ["coolray", "кулрей"], "Atlas": ["atlas", "атлас"], "Atlas Pro": ["atlas pro"],
              "Emgrand": ["emgrand", "эмгранд"], "Monjaro": ["monjaro", "монджаро"], "Tugella": ["tugella"], "MK": ["mk"]},
    "Chery": {"Tiggo 7 Pro Max": ["tiggo 7 pro max"], "Tiggo 7 Pro": ["tiggo 7 pro"], "Tiggo 8 Pro Max": ["tiggo 8 pro max"],
              "Tiggo 8 Pro": ["tiggo 8 pro"], "Tiggo 4 Pro": ["tiggo 4 pro"], "Tiggo 4": ["tiggo 4"],
              "Tiggo 7": ["tiggo 7"], "Tiggo 8": ["tiggo 8"], "Tiggo 2": ["tiggo 2"], "Tiggo 3": ["tiggo 3"],
              "Tiggo 5": ["tiggo 5"], "Tiggo": ["tiggo", "тигго", "suv t11", "t11"], "Arrizo 8": ["arrizo 8"],
              "Very": ["very", "a13"], "Bonus": ["bonus"], "Amulet": ["amulet", "амулет"], "Fora": ["fora"],
              "Kimo": ["kimo"], "IndiS": ["indis"], "M11": ["m11"]},
    "Audi": {"A4": ["a4", "а4"], "A6": ["a6", "а6"], "Q5": ["q5"], "Q7": ["q7"], "A3": ["a3", "а3"], "Q3": ["q3"],
             "A5": ["a5"], "A8": ["a8"], "A7": ["a7"]},
    "UAZ": {"Patriot": ["patriot", "патриот"], "Hunter": ["hunter", "хантер"], "Pickup": ["pickup", "пикап"]},
    "Suzuki": {"SX4": ["sx4", "сх4"], "Grand Vitara": ["grand vitara", "гранд витара"], "Vitara": ["vitara", "витара"],
               "Swift": ["swift", "свифт"], "Jimny": ["jimny", "джимни"], "Liana": ["liana"], "Kei": ["kei"],
               "Wagon R Solio": ["wagon r solio"], "Wagon R": ["wagon r"], "Solio": ["solio"], "Splash": ["splash"],
               "Escudo": ["escudo"]},
    "Land Rover": {"Range Rover": ["range rover", "рендж ровер", "рейндж ровер", "рейндж", "рендж"], "Range Rover Sport": ["range rover sport"],
                   "Range Rover Evoque": ["range rover evoque", "evoque"], "Discovery": ["discovery", "дискавери"],
                   "Discovery Sport": ["discovery sport"], "Freelander": ["freelander", "фрилендер"], "Defender": ["defender"]},
    "Great Wall": {"Hover": ["hover", "ховер", "cc6460", "cc 6460", "cc460"], "Coolbear": ["coolbear"], "Wingle": ["wingle"],
                   "Safe": ["safe"], "Deer": ["deer"]},
    "Haval": {"Jolion": ["jolion", "джолион"], "F7": ["f7"], "F7x": ["f7x"], "H6": ["h6"], "H9": ["h9"],
              "Dargo": ["dargo"], "M6": ["m6"], "H2": ["h2"]},
    "Peugeot": {"308": ["308"], "207": ["207"], "206": ["206"], "408": ["408"], "407": ["407"], "3008": ["3008"],
                "Partner": ["partner"], "307": ["307"], "4007": ["4007"], "508": ["508"]},
    "Citroen": {"C4": ["c4"], "C3": ["c3"], "C5": ["c5"], "C4 Picasso": ["c4 picasso", "с4 пикассо"], "C3 Picasso": ["c3 picasso", "с3 пикассо"],
                "C-Elysee": ["c-elysee", "c-elysée"], "Berlingo": ["berlingo"], "C-Crosser": ["c-crosser"],
                "Xsara": ["xsara"], "Jumper": ["jumper", "l4h2"]},
    "Volvo": {"S80": ["s80"], "XC90": ["xc90", "xc 90"], "XC60": ["xc60", "xc 60"], "S60": ["s60"], "S40": ["s40"], "V50": ["v50"],
              "XC70": ["xc70", "xc 70"], "V40": ["v40"]},
    "SsangYong": {"Rexton": ["rexton", "рекстон"], "Kyron": ["kyron", "кайрон"], "Actyon": ["actyon", "актион"],
                  "Actyon Sports": ["actyon sports"], "Istana": ["istana"], "Musso": ["musso"], "Stavic": ["stavic"]},
    "Changan": {"CS35 Plus": ["cs35 plus", "cs35plus"], "CS35": ["cs35"], "CS55 Plus": ["cs55 plus"], "CS55": ["cs55"],
                "CS75 Plus": ["cs75 plus"], "CS75": ["cs75"], "UNI-K": ["uni-k"], "UNI-T": ["uni-t"], "UNI-V": ["uni-v"],
                "Eado": ["eado"], "Alsvin": ["alsvin"]},
    "Exeed": {"LX": ["lx"], "TXL": ["txl"], "VX": ["vx"]},
    "Omoda": {"C5": ["c5"], "S5": ["s5"]},
    "Lifan": {"Solano": ["solano", "солано", "214813"], "X60": ["x60", "215800"], "Smily": ["smily", "113300"], "Breez": ["breez"], "Celliya": ["celliya"],
              "Cebrium": ["cebrium"], "Myway": ["myway"], "X50": ["x50"]},
    "Vortex": {"Tingo": ["tingo"], "Estina": ["estina"], "Corda": ["corda"]},
    "FAW": {"X80": ["x80"], "V5": ["v5"], "V2": ["v2"], "Besturn": ["besturn"], "Oley": ["oley"]},
    "Fiat": {"Albea": ["albea", "альбеа"], "Punto": ["punto"], "Doblo": ["doblo", "добло"], "Ducato": ["ducato"],
             "Linea": ["linea"], "Bravo": ["bravo"], "Panda": ["panda"]},
    "Dodge": {"Caravan": ["caravan", "караван"], "Intrepid": ["intrepid", "интрепид"], "Caliber": ["caliber"],
              "Stratus": ["stratus"], "Journey": ["journey"], "Neon": ["neon"], "Ram": ["ram"]},
    "Jeep": {"Grand Cherokee": ["grand cherokee", "гранд чероки"], "Cherokee": ["cherokee", "чероки"],
             "Compass": ["compass"], "Liberty": ["liberty"], "Wrangler": ["wrangler"]},
    "Moskvich": {"3": ["3"], "2141": ["2141"], "412": ["412"], "2140": ["2140"]},
    "Porsche": {"Cayenne": ["cayenne", "кайен"], "Panamera": ["panamera"], "Macan": ["macan"]},
    "Jaguar": {"XF": ["xf"], "XJ": ["xj"], "F-Pace": ["f-pace"], "XE": ["xe"]},
    "Datsun": {"on-DO": ["on-do", "on do", "он-до", "он до"], "mi-DO": ["mi-do", "mi do"]},
    "Subaru": {"Impreza": ["impreza", "импреза"], "Forester": ["forester", "форестер"], "Legacy": ["legacy", "легаси"],
               "Outback": ["outback", "аутбек"], "Tribeca": ["tribeca", "трибека"], "XV": ["xv"]},
    "Zotye": {"T600": ["t600"], "Coupa": ["coupa"]},
    "Daihatsu": {"YRV": ["yrv"], "Terios": ["terios"], "Boon": ["boon"], "Move": ["move"]},
}

LADA_CODES = {"1117": "Kalina", "1118": "Kalina", "1119": "Kalina", "2192": "Kalina", "2194": "Kalina",
              "2170": "Priora", "2171": "Priora", "2172": "Priora", "2190": "Granta", "2191": "Granta",
              "2180": "Vesta", "2181": "Vesta", "1111": "Oka", "2121": "4x4", "2131": "4x4",
              "RS0": "Largus", "KS0": "Largus", "GAB": "XRAY", "GFK": "Vesta", "GFL": "Vesta"}
MERCEDES_RE = re.compile(r"(?<![a-z])(cla|cls|clk|gla|glb|glc|gle|glk|gls|gl|ml|slk|sl|[abcegsv])\s*-?\s*(?:class|класс|\d{2,3})", re.I)
MERCEDES_NAMES = {"ml": "M-Class", "gl": "GL-Class", "glk": "GLK-Class", "clk": "CLK-Class", "sl": "SL-Class", "slk": "SLK-Class"}
BMW_RES = [
    (re.compile(r"(?<![a-z0-9])(x[1-7]|z[348]|i[38])(?![0-9])", re.I), lambda m: m.group(1).upper()),
    (re.compile(r"(?<![a-z0-9])([1-8])\s*(?:series|серии|серия)", re.I), lambda m: f"{m.group(1)} Series"),
    (re.compile(r"(?<![a-z0-9])([1-8])\d{2}(?:[a-z]{0,3})(?![0-9])", re.I), lambda m: f"{m.group(1)} Series"),
]
LETTER_MODEL_RE = re.compile(r"(?<![a-z0-9])(qx\d{2}|[a-z]{1,2})\s*-?\s*\d{2,3}[a-z]{0,2}(?![0-9])", re.I)
HOMOGLYPHS = str.maketrans("АВСЕНКМОРТХаеорсху", "ABCEHKMOPTXaeopcxy")
MODEL_STOPWORDS = {"модель", "модели", "марка", "марки", "автомобиль", "легковой", "года", "г", "vin", "лот", "тс",
                   "new", "седан", "хэтчбек", "универсал", "транспортное", "средство", "цвет", "гос", "номер", "грз"}
TOKEN_RE = re.compile(r"[A-Za-zА-Яа-яЁё0-9]+")

YEAR_RES = [
    re.compile(r"год\w*\s*(?:выпуска|изготовления|производства)\D{0,20}((?:19|20)\d\d)", re.I),
    re.compile(r"\b((?:19|20)\d\d)\s*,?\s*(?:г\.?\s*в|г/в|гв\b|года?\b|г\.)", re.I),
    re.compile(r"г\.?\s*в\.?\s*[:\-–]?\s*((?:19|20)\d\d)\b", re.I),
    re.compile(r"[,;]\s*((?:19|20)\d\d)\s*[,;]"),
]
NUMBER = r"(\d+(?:[.,]\d+)?)"
POWER_CONTEXT_RE = re.compile(r"мощност|л\.?\s*с\b|квт", re.I)
POWER_HP_RES = [
    re.compile(r"квт\s*/\s*л\.?\s*с\.?\)?\s*:?\s*/\s*" + NUMBER, re.I),
    re.compile(NUMBER + r"\s*л\.?\s*с", re.I),
    re.compile(r"л\.?\s*с\.?\s*(?:\(\s*квт\.?\s*\))?\s*[:\-–]?\s*" + NUMBER + r"(?!\s*(?:/|квт))", re.I),
]
POWER_KW_RES = [
    re.compile(NUMBER + r"\s*квт", re.I),
    re.compile(r"квт\.?\)?\s*(?:\([^)]*\))?\s*[:\-–]?\s*" + NUMBER + r"(?!\s*(?:/|л\.?\s*с))", re.I),
]
VOLUME_RE = re.compile(r"об+[ъь]?[её]м\w*", re.I)
VOLUME_UNITS_RE = re.compile(r"см\s*[23³?]|куб\.?\s*см|см\.?\s*куб", re.I)
VOLUME_CC_RE = re.compile(r"(\d{3,4}(?:[.,]\d+)?)\s*(?:куб|см3|см³)", re.I)

NEGATION_BEFORE = re.compile(r"(?:\bне\s+(?:является\s+)?(?:предметом\s+)?|\bнет\s+|\bбез\s+|отсутстви\w*\s+|отсутству\w*\s+"
                             r"|(?:в\s+случае|при)\s+(?:наличи\w*|выявлени\w*)\s+(?:\w+\s+){0,2}|не\s+найден\w*\s+(?:\w+\s+){0,3})$", re.I)
NEGATION_AFTER = re.compile(r"^[\w\s()]{0,40}?(?:[:\-–]\s*(?:нет|отсутству)|\s+не\s+является|\s+отсутству)", re.I)
FLAG_PATTERNS = {
    "major_defect": r"не\s+на\s*ходу|не\s+ходу|не\s+заводится|не\s+эксплуатир|заклин"
                    r"|годн\w*\s+остат|на\s+запчаст|разукомплект|для\s+разбор|(?:отсутству\w*|без|нет)\s+(?:двигател|двс)"
                    r"|(?:тс|автомобиль|транспортное средство)\s+неисправ|неисправн\w*\s+(?:двигател|акпп|мкпп|кпп|коробк|вариатор)"
                    r"|(?:двигател\w*|двс|акпп|мкпп|кпп|коробк\w*(?:\s+передач)?|вариатор\w*)\s+(?:не\s*исправ|неисправ|сломан|лопнул|требует\s+ремонт)"
                    r"|(?:двигател\w*|коробк\w*)[^.]{0,25}сломан|капитальн\w*\s+ремонт|отказ\w*\s+(?:работы\s+)?(?:двигател|акпп|мкпп|кпп|коробк)"
                    r"|дефект\w*\s+(?:двс|двигател|акпп|кпп|вариатор)|проблем\w*\s+с\s+(?:двигател|акпп|кпп|коробк)"
                    r"|(?:ремонт|замен\w*)\s+(?:двигател|акпп|мкпп|кпп|коробк)|порван\w*\s+ремень|ремень\s+грм\s+порвал"
                    r"|отсутствуют\s+узлы\s+и\s+агрегаты",
    "damaged": r"дтп|после\s+аварии|деформац|коррози|ржавч|гнил|вмятин|замяти|помят|разбит|битый|треснут|трещин"
               r"|поврежден\w*\s+(?:кузов|двер|бампер|крыл|крыш|кап)|повреждени\w*\s+(?:кузова|лкп)|с\s+повреждениями"
               r"|дефект\w*\s+(?:по\s+)?кузов|замен\w*\s+(?:капота|бампера|двер|крыл|лобового|порогов)"
               r"|кузовн\w*\s+ремонт|сварочн|переварк|состояние\s+кузова\s+неудовлетвор",
    "no_keys_or_docs": r"(?:отсутству\w*|без|нет|утерян\w*|утрачен\w*)\s+(?:ключ|птс|паспорт|стс|свидетельств|документ)"
                       r"|(?:ключ|птс|стс|документ)(?:(?!шасси|рам|vin|кузов|номер|двигател)[^.;:]){0,40}?(?:отсутству|утерян|утрачен|\bнет\b)",
    "pledge": r"залог|залож",
    "arrest_or_ban": r"арест|запрет\w*\s+(?:на\s+регистрац|регистрац|фссп)|ограничени\w*\s+(?:на\s+регистрац|судебн)"
                     r"|наложенных\s+ограничений|имеет\s+обременения,\s+ограничения",
    "location_unknown": r"местонахождени\w*\s+(?:не\s*известно|неизвестно|не\s+установлено)|не\s+передан\w*\s+(?:\w+\s+)?управляющ"
                        r"|управляющ\w*\s+не\s+передан|уклоняется\s+от\s+передачи|розыск|отсутствует\s+в\s+натуре"
                        r"|осмотр\s+(?:\w+\s+){0,4}?(?:невозможен|не\s+производился)",
}
FLAG_RES = {name: re.compile(pattern, re.I) for name, pattern in FLAG_PATTERNS.items()}


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _alias_regex(alias: str) -> re.Pattern:
    body = re.sub(r"\\[ \-]", r"[\\s\\-_]*", re.escape(alias))
    end = r"(?![a-zа-яё0-9])" if alias[-1].isdigit() else r"(?![a-zа-яё])"
    return re.compile(r"(?<![a-zа-яё0-9])" + body + end, re.I)


def _alias_patterns(names: dict[str, list[str]]) -> list[tuple[str, re.Pattern]]:
    return [(name, _alias_regex(alias)) for name, aliases in names.items() for alias in aliases]


MAKE_ALIASES = _alias_patterns(MAKES)
MODEL_ALIASES = {make: _alias_patterns(models) for make, models in MODELS.items()}


def _first_hit(text: str, patterns: list[tuple[str, re.Pattern]]) -> tuple[str, re.Match] | None:
    hits = [(m.start(), -len(m.group()), name, m) for name, pattern in patterns if (m := pattern.search(text))]
    if not hits:
        return None
    _, _, name, m = min(hits, key=lambda h: h[:3])
    return name, m


def extract_make(text: str) -> str | None:
    hit = _first_hit(text, MAKE_ALIASES)
    return hit[0] if hit else None


def _lada_from_code(text: str) -> str | None:
    for m in re.finditer(r"(?<![A-Za-z0-9])([A-Z]{2,3}\d{3}|\d{4,6})(?![A-Za-z0-9])", text, re.I):
        code = m.group(1).upper()
        for prefix, model in LADA_CODES.items():
            if code.startswith(prefix):
                return model
        if code.startswith("21099"):
            return "21099"
        if code.isdigit() and code.startswith("21"):
            return code[:4]
    return None


def _special_model(make: str, window: str) -> str | None:
    window = window.translate(HOMOGLYPHS)
    if make == "Mercedes-Benz":
        if m := MERCEDES_RE.search(window):
            letters = m.group(1).lower()
            return MERCEDES_NAMES.get(letters, f"{letters.upper()}-Class" if len(letters) == 1 else letters.upper())
        return None
    if make == "BMW":
        for pattern, name in BMW_RES:
            if m := pattern.search(window):
                return name(m)
        return None
    if make in ("Lexus", "Infiniti") and (m := LETTER_MODEL_RE.search(window)):
        return m.group(1).upper()
    return None


def _clean_token(token: str) -> str:
    if any(ch.isdigit() for ch in token):
        token = token.translate(HOMOGLYPHS)
    if token.isupper() and len(token) > 3 and not any(ch.isdigit() for ch in token):
        return token.capitalize()
    return token


def _model_in(text: str, make: str) -> str | None:
    make_hit = _first_hit(text, [(n, p) for n, p in MAKE_ALIASES if n == make])
    if make_hit is None:
        return None
    window = text[make_hit[1].start():make_hit[1].start() + 120]
    hits = [h for w in (window, window.translate(HOMOGLYPHS)) if (h := _first_hit(w, MODEL_ALIASES.get(make, [])))]
    if hits:
        return min(hits, key=lambda h: (h[1].start(), -len(h[1].group())))[0]
    if make == "Lada" and (model := _lada_from_code(window)):
        return model
    if make in ("Mercedes-Benz", "BMW", "Lexus", "Infiniti"):
        return _special_model(make, window)
    for token in TOKEN_RE.findall(text[make_hit[1].end():make_hit[1].end() + 40]):
        if token.lower() in MODEL_STOPWORDS or re.fullmatch(r"(19|20)\d\d", token) or extract_make(token):
            continue
        if make in ("GAZ", "UAZ", "MAZ", "KAMAZ", "Moskvich") and token.isdigit():
            return token[:5]
        return _clean_token(token)
    return None


def extract_model(texts: list[str], make: str | None) -> str | None:
    if make is None:
        return None
    for text in texts:
        if model := _model_in(text, make):
            return model
    return None


def extract_year(text: str) -> int | None:
    for pattern in YEAR_RES:
        if m := pattern.search(text):
            return int(m.group(1))
    return None


def _power_pair(window: str) -> float | None:
    numbers = [_to_float(n) for n in re.findall(r"\d+(?:[.,]\d+)?", window)]
    for a, b in zip(numbers, numbers[1:]):
        low, high = sorted((a, b))
        if low > 0 and 1.3 <= high / low <= 1.42 and 30 <= high <= 800:
            return high
    return None


def extract_power_hp(text: str) -> float | None:
    for m in POWER_CONTEXT_RE.finditer(text):
        if value := _power_pair(text[m.start():m.start() + 60]):
            return value
    for pattern in POWER_HP_RES:
        if (m := pattern.search(text)) and 30 <= (value := _to_float(m.group(1))) <= 800:
            return value
    for pattern in POWER_KW_RES:
        if (m := pattern.search(text)) and 20 <= (value := _to_float(m.group(1))) <= 600:
            return round(value * 1.36, 1)
    return None


def _volume(raw: str) -> float | None:
    value = _to_float(raw)
    if value < 10:
        value *= 1000
    return round(value) if 600 <= value <= 8000 else None


def extract_engine_cc(text: str) -> float | None:
    for m in VOLUME_RE.finditer(text):
        window = VOLUME_UNITS_RE.sub(" ", text[m.end():m.end() + 40])
        if (n := re.search(r"\d+(?:[.,]\d+)?", window)) and (value := _volume(n.group())):
            return value
    for m in VOLUME_CC_RE.finditer(text):
        if value := _volume(m.group(1)):
            return value
    return None


def _is_negated(text: str, m: re.Match) -> bool:
    return bool(NEGATION_BEFORE.search(text[max(0, m.start() - 50):m.start()]) or NEGATION_AFTER.search(text[m.end():m.end() + 60]))


def extract_flags(text: str) -> dict[str, int]:
    return {name: int(any(not _is_negated(text, m) for m in pattern.finditer(text))) for name, pattern in FLAG_RES.items()}


def extract_features(title: str | None, info: str | None) -> dict:
    title, info = title or "", info or ""
    text = f"{title} {info}"
    make = extract_make(info) or extract_make(title)
    return {
        "make": make,
        "model": extract_model([info, title], make),
        "year": extract_year(info) or extract_year(title),
        "power_hp": extract_power_hp(info),
        "engine_cc": extract_engine_cc(info),
        **extract_flags(text),
    }


def extract_frame(df: pd.DataFrame) -> pd.DataFrame:
    rows = [extract_features(title, info) for title, info in zip(df["lot_title"], df["lot_info"])]
    return pd.DataFrame(rows, index=df.index)
