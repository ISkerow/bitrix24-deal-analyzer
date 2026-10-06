"""Генерирует синтетический датасет sample_data.csv.

Структура колонок повторяет реальную выгрузку crm.deal.list,
но все значения выдуманы: случайные даты, вымышленные источники,
случайные суммы. Никакой связи с реальными сделками нет.

Датасет собран так, чтобы каждый отчёт analyze.py имел что показать:
  - один месяц содержит 20+ WhatsApp-заявок (порог помесячной таблицы);
  - часть заявок застряла на C15:NEW, часть выиграна с суммой;
  - есть обе воронки и сделки с нулевым лагом ("ни разу не открывали").

Запуск:
    python generate_sample.py
"""

import random
from datetime import datetime, timedelta

import pandas as pd

SEED = 42
N_ROWS = 45
OUT = "sample_data.csv"

# Вымышленные ID коннекторов в стиле открытых линий Bitrix24.
WHATSAPP_SOURCES = ["WZ1a2b3c4d", "WZ9f8e7d6c", "21|DEMO_CHATS_WHATSAPP"]
OTHER_SOURCES = ["CALL", "CALLBACK", "WEB", "WEBFORM", "RECOMMENDATION", "RC_GENERATOR"]

OLD_STAGES = ["NEW", "PREPARATION", "EXECUTING", "WON", "LOSE"]
NEW_STAGES = ["C15:NEW", "C15:PREPARATION", "C15:WON", "C15:LOSE"]

COMMENTS = ["", "", "", "перезвонить", "интересует наличие", "думает", "уточнить условия"]


def _iso(dt: datetime) -> str:
    """Дата в формате Bitrix24: ISO8601 с фиксированным смещением +03:00."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")


def make_rows() -> list[dict]:
    """Собирает список синтетических сделок с воспроизводимым random."""
    rng = random.Random(SEED)
    rows = []

    for i in range(N_ROWS):
        # Первые 24 строки — WhatsApp-заявки одного месяца (2024-05),
        # чтобы помесячная таблица прошла порог MIN_MONTH_DEALS.
        if i < 24:
            source = rng.choice(WHATSAPP_SOURCES)
            created = datetime(2024, 5, 1) + timedelta(
                days=rng.randint(0, 27), hours=rng.randint(8, 20), minutes=rng.randint(0, 59)
            )
            # Больше половины намеренно застряло — демонстрация срыва процесса.
            stage = rng.choice(["C15:NEW"] * 6 + ["C15:WON", "C15:LOSE", "C15:PREPARATION", "C15:LOSE"])
        else:
            source = rng.choice(OTHER_SOURCES + WHATSAPP_SOURCES[:1])
            created = datetime(2024, rng.randint(1, 4), rng.randint(1, 28), rng.randint(8, 20))
            stage = rng.choice(OLD_STAGES + NEW_STAGES)

        # Застрявшие не трогали вовсе (нулевой лаг), остальные меняли позже.
        if stage == "C15:NEW" and rng.random() < 0.6:
            modified = created
        else:
            modified = created + timedelta(hours=rng.randint(1, 400))

        won = stage in ("WON", "C15:WON")
        opportunity = round(rng.uniform(500_000, 5_000_000), 2) if won and rng.random() < 0.8 else 0.0

        rows.append({
            "ID": 1000 + i,
            "SOURCE_ID": source,
            "DATE_CREATE": _iso(created),
            "DATE_MODIFY": _iso(modified),
            "ASSIGNED_BY_ID": rng.choice([101, 102, 103, 104]),
            "COMMENTS": rng.choice(COMMENTS),
            "STAGE_ID": stage,
            "OPPORTUNITY": opportunity,
        })
    return rows


def main() -> None:
    """Пишет синтетический датасет в sample_data.csv."""
    df = pd.DataFrame(make_rows())
    df.to_csv(OUT, index=False)
    print(f"сохранено: {OUT} ({len(df)} строк, колонки: {', '.join(df.columns)})")


if __name__ == "__main__":
    main()
