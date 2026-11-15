"""Генерирует синтетический датасет sample_data.csv.

ДАННЫЕ СИНТЕТИЧЕСКИЕ: все значения выдуманы — даты, источники, суммы,
имена менеджеров. Никакой связи с реальными сделками и людьми нет.

Формат — как у выгрузки сделок из интерфейса Битрикс24: русские названия
колонок, разделитель «;», даты ДД.ММ.ГГГГ ЧЧ:ММ:СС, UTF-8 с BOM.
Колонок меньше, чем в настоящей выгрузке: только те, что нужны анализу,
плюс «Название сделки», «Валюта» и «Комментарий» — показать, что лишнее
отбрасывается при загрузке.

Сюжет примера: шесть месяцев, поток заявок растёт. Первые четыре месяца
WhatsApp-заявки почти все обрабатываются, в последние два доля застрявших
резко растёт — это и должна показать помесячная таблица.

Запуск:
    python generate_sample.py
"""

import calendar
import random
from datetime import datetime, timedelta

import pandas as pd

SEED = 42
OUT = "sample_data.csv"

# (год, месяц, сколько сделок, доля застрявших в WhatsApp, доля застрявших в остальных каналах)
MONTHS = [
    (2026, 5, 80, 0.04, 0.03),
    (2026, 6, 90, 0.05, 0.03),
    (2026, 7, 100, 0.06, 0.04),
    (2026, 8, 110, 0.08, 0.04),
    (2026, 9, 150, 0.45, 0.08),
    (2026, 10, 170, 0.68, 0.10),
]  # всего 700 сделок

# Источник и его вес: чем больше вес, тем чаще встречается.
SOURCES = {"WhatsApp": 45, "Звонок": 25, "Обратный звонок": 5, "Веб-сайт": 15, "Рекомендация": 10}

# Стадии обработанных сделок и их веса. «Новая» назначается отдельно.
DONE_STAGES = {
    "В работе": 30,
    "Подготовка документов": 20,
    "Счёт на предоплату": 10,
    "Сделка успешна": 13,
    "Сделка провалена": 27,
}

# Вымышленные менеджеры и их доля заявок.
MANAGERS = {"Алия Примерова": 35, "Данияр Тестов": 30, "Марат Образцов": 20, "Ольга Демонстрова": 15}

COMMENTS = ["", "", "", "перезвонить", "интересует наличие", "думает", "уточнить условия"]


def _pick(rng: random.Random, weighted: dict[str, int]) -> str:
    """Случайный ключ словаря с учётом весов."""
    return rng.choices(list(weighted), weights=list(weighted.values()))[0]


def _fmt(dt: datetime) -> str:
    """Дата в формате выгрузки из интерфейса: ДД.ММ.ГГГГ ЧЧ:ММ:СС."""
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def _created(rng: random.Random, year: int, month: int) -> datetime:
    """Случайный момент в месяце: 70% заявок — с 9 до 18, остальные — в любое время."""
    day = rng.randint(1, calendar.monthrange(year, month)[1])
    hour = rng.randint(9, 17) if rng.random() < 0.7 else rng.choice([0, 7, 8, 18, 19, 20, 21, 22, 23])
    return datetime(year, month, day, hour, rng.randint(0, 59), rng.randint(0, 59))


def make_rows() -> list[dict]:
    """Собирает список синтетических сделок с воспроизводимым random."""
    rng = random.Random(SEED)
    rows = []

    for year, month, n_deals, wa_stuck, other_stuck in MONTHS:
        for _ in range(n_deals):
            source = _pick(rng, SOURCES)
            created = _created(rng, year, month)

            stuck = rng.random() < (wa_stuck if source == "WhatsApp" else other_stuck)
            stage = "Новая" if stuck else _pick(rng, DONE_STAGES)

            # Большинство застрявших не трогали вовсе, остальные меняли позже.
            if stuck and rng.random() < 0.7:
                modified = created
            else:
                modified = created + timedelta(minutes=rng.randint(3, 10 * 24 * 60))

            won = stage == "Сделка успешна"
            amount = rng.randrange(50_000, 900_000, 5_000) if won and rng.random() < 0.85 else 0

            rows.append({
                "created": created,
                "Воронка": "Общая воронка",
                "Стадия сделки": stage,
                "Ответственный": _pick(rng, MANAGERS),
                "Источник": source,
                "Сумма": f"{amount:.2f}",
                "Валюта": "Тенге",
                "Дата создания": _fmt(created),
                "Дата изменения": _fmt(modified),
                "Комментарий": rng.choice(COMMENTS),
            })

    # ID растут по времени создания, как в CRM; в выгрузке новые сделки сверху.
    rows.sort(key=lambda r: r["created"])
    for i, row in enumerate(rows):
        del row["created"]
        row["ID"] = 1000 + 2 * i
        row["Название сделки"] = f"Сделка #{row['ID']}"
    rows.reverse()
    return rows


def main() -> None:
    """Пишет синтетический датасет в sample_data.csv."""
    columns = ["ID", "Воронка", "Стадия сделки", "Ответственный", "Название сделки", "Источник",
               "Сумма", "Валюта", "Дата создания", "Дата изменения", "Комментарий"]
    df = pd.DataFrame(make_rows())[columns]
    df.to_csv(OUT, sep=";", index=False, encoding="utf-8-sig")
    print(f"сохранено: {OUT} ({len(df)} строк, данные синтетические)")


if __name__ == "__main__":
    main()
