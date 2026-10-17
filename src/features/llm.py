import json
from pathlib import Path

import httpx
import pandas as pd

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3:8b"
CACHE_PATH = Path("data/interim/llm_cache.jsonl")
FLAGS = ["major_defect", "damaged", "no_keys_or_docs", "pledge", "arrest_or_ban", "location_unknown"]

SYSTEM_PROMPT = """Ты извлекаешь характеристики легкового автомобиля из текста лота торгов по банкротству. Отвечай только JSON по схеме.

make: марка латиницей в общепринятом написании (Lada, Kia, Hyundai, Mercedes-Benz, Great Wall, GAZ, UAZ, Moskvich). ВАЗ и LADA - это Lada.
model: модель латиницей в общепринятом написании, без комплектации, двигателя и кода кузова (Corolla, а не Corolla 1.6 AT; Tiggo 7 Pro Max и Tiggo 7 Pro - разные модели; Range Rover Sport, Santa Fe, Corolla Fielder, Lancer Cedia пишутся полностью).
  Lada: Granta, Kalina, Priora, Vesta, Largus, XRAY, 4x4 (Нива, 2121, 21214, 2131), Oka (1111). Остальные ВАЗ - номер модели из 4 цифр без модификации: 21099, 2106, 2107, 2110 (21102), 2111 (21110), 2112 (21124), 2113 (211340), 2114 (21144, 211440), 2115 (21150).
  Mercedes-Benz: класс (C-Class, E-Class, S-Class, M-Class для ML, GL-Class, V-Class; GLA, GLC, GLE, CLA без -Class). BMW: серия (3 Series, 5 Series, 7 Series) или X1-X7.
  Регистрационные имена: Renault SR = Logan, Chevrolet KLAN = Lacetti, Chevrolet KLAC = Captiva, Chevrolet KLAU = Rezzo.
  Если модель указана только кодом и название не восстанавливается, верни код.
year: год выпуска, только если он указан в тексте, иначе null.
power_hp: мощность в л.с., если указана. Если даны кВт и л.с., бери л.с. (большее число). Если только кВт, умножь на 1.36. Иначе null.
engine_cc: рабочий объём в куб. см, только если указан явно (1,6 л -> 1600). Объём в названии модели не считается. Иначе null.
exclude: true, если лот не один легковой автомобиль (грузовик, фургон, микроавтобус, прицеп, мотоцикл, несколько ТС).
Флаги (true/false), только по тексту:
  major_defect: серьёзная неисправность - не на ходу, не заводится, нужен ремонт или замена двигателя или КПП, капитальный ремонт. Мелочи (аккумулятор, подвеска, магнитола) не считаются. Уже выполненный ремонт не считается.
  damaged: повреждения кузова - ДТП, вмятины, коррозия, деформация, разбитые или треснутые стёкла и детали. Мелкие сколы и потёртости не считаются.
  no_keys_or_docs: нет ключей, ПТС, СТС или других документов.
  pledge: имущество в залоге (в том числе если это сказано только в названии лота). "Не является предметом залога" - false.
  arrest_or_ban: арест, запрет на регистрационные действия, ограничения приставов или суда. Оговорки "в случае наличия ограничений" и "ограничения не найдены" - false.
  location_unknown: местонахождение неизвестно, ТС не передано управляющему, в розыске, отсутствует в натуре, осмотр невозможен. Указание места хранения - false.
Флаги независимы: "не на ходу: порван ремень ГРМ" - только major_defect."""

SCHEMA = {
    "type": "object",
    "properties": {
        "make": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "year": {"type": ["integer", "null"]},
        "power_hp": {"type": ["number", "null"]},
        "engine_cc": {"type": ["number", "null"]},
        "exclude": {"type": "boolean"},
        **{flag: {"type": "boolean"} for flag in FLAGS},
    },
    "required": ["make", "model", "year", "power_hp", "engine_cc", "exclude", *FLAGS],
}


def _load_cache() -> dict[int, dict]:
    if not CACHE_PATH.exists():
        return {}
    rows = (json.loads(line) for line in CACHE_PATH.read_text().splitlines() if line)
    return {row["tradeId"]: row for row in rows if row.get("model_name") == MODEL}


def extract_one(client: httpx.Client, title: str | None, info: str | None) -> dict:
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": f"Название лота: {title or ''}\nОписание: {info or ''}"}],
        "format": SCHEMA,
        "think": False,
        "stream": False,
        "options": {"temperature": 0, "seed": 42},
    }
    response = client.post(OLLAMA_URL, json=payload, timeout=300)
    response.raise_for_status()
    result = json.loads(response.json()["message"]["content"])
    return {**result, **{flag: int(bool(result.get(flag))) for flag in FLAGS}}


def extract_frame(df: pd.DataFrame) -> pd.DataFrame:
    cache = _load_cache()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client() as client, CACHE_PATH.open("a") as out:
        for trade_id, title, info in zip(df["tradeId"], df["lot_title"], df["lot_info"]):
            if trade_id not in cache:
                cache[trade_id] = {"tradeId": int(trade_id), "model_name": MODEL, **extract_one(client, title, info)}
                out.write(json.dumps(cache[trade_id], ensure_ascii=False) + "\n")
                out.flush()
            rows.append(cache[trade_id])
    return pd.DataFrame(rows, index=df.index).drop(columns=["tradeId", "model_name"])
