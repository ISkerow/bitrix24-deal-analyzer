"""Анализ обработки заявок в CRM Bitrix24 (обезличенный пример).

Что делает:
  - классифицирует сделки по каналам (WhatsApp / звонок / прочее)
    и воронкам (старая / новая);
  - считает долю и возраст необработанных заявок;
  - строит помесячную таблицу срыва обработки WhatsApp-канала;
  - оценивает упущенные продажи через конверсию и средний чек.

Методические решения (см. докстринги модулей в src/):
  1. Токен API — только в переменной окружения BITRIX_WEBHOOK.
  2. Точка отсчёта — максимальная дата в данных, а не now(),
     иначе метрика растёт каждый день сама по себе.
  3. Метрики названы честно: не "скорость ответа",
     а "возраст необработанной заявки".
  4. Медиана вместо среднего — данные с длинным хвостом.
  5. Старая и новая воронки разделены.
  6. SOURCE_ID сведён в понятные каналы.
  7. Заполненность полей проверяется до использования поля.

Запуск:
    python analyze.py                    # анализ sample_data.csv
    python analyze.py path/to/data.xlsx  # анализ своей выгрузки
    export BITRIX_WEBHOOK="https://<portal>.bitrix24.<tld>/rest/<id>/<token>/"
    python analyze.py --fetch            # выгрузить из API и проанализировать
"""

import os
import sys

from src.config import DEFAULT_DATA_FILE
from src.fetch import fetch_deals
from src.prepare import field_coverage, load, prepare
from src.reports import (
    report_lag,
    report_money,
    report_pipelines,
    report_stuck,
    report_whatsapp_monthly,
)


def main() -> None:
    """Точка входа: загружает данные, готовит их и печатает все отчёты."""
    args = [a for a in sys.argv[1:] if a != "--fetch"]
    if "--fetch" in sys.argv:
        raw = fetch_deals()
    else:
        path = args[0] if args else DEFAULT_DATA_FILE
        if not os.path.exists(path):
            sys.exit(f"Нет файла {path}. Укажи путь к данным или запусти с --fetch")
        raw = load(path)

    df = prepare(raw)

    print(f"\nЗагружено сделок: {len(df)}")
    print(f"Период: {df['created'].min().date()} — {df['created'].max().date()}")

    field_coverage(df)
    report_pipelines(df)
    report_stuck(df)
    report_whatsapp_monthly(df)
    report_lag(df)
    report_money(df)

    print("\n" + "=" * 60)
    print("Реальные данные не публикуются: только агрегаты, без строк и названий.")
    print("=" * 60)


if __name__ == "__main__":
    main()
