"""Выгрузка сделок из Bitrix24 REST API.

Токен берётся только из переменной окружения BITRIX_WEBHOOK —
в коде и в репозитории его быть не должно.
"""

import os
import sys
import time

import pandas as pd

from .config import RAW_XLSX

FIELDS = [
    "ID", "SOURCE_ID", "STAGE_ID", "CATEGORY_ID",
    "DATE_CREATE", "DATE_MODIFY",
    "ASSIGNED_BY_ID", "OPPORTUNITY", "CLOSED",
]


def fetch_deals(out_path: str = RAW_XLSX) -> pd.DataFrame:
    """Постранично выгружает все сделки портала и сохраняет их в xlsx.

    Возвращает выгрузку как DataFrame. Завершает процесс с ошибкой,
    если не задан BITRIX_WEBHOOK или API вернул ошибку.
    """
    base = os.environ.get("BITRIX_WEBHOOK")
    if not base:
        sys.exit("Не задана переменная окружения BITRIX_WEBHOOK")

    import requests

    params = {f"select[{i}]": f for i, f in enumerate(FIELDS)}

    rows, start, page = [], 0, 1
    while True:
        params["start"] = start
        r = requests.get(f"{base}crm.deal.list", params=params, timeout=30)
        data = r.json()
        if "error" in data:
            sys.exit(f"Ошибка API: {data.get('error_description')}")

        rows.extend(data.get("result", []))
        print(f"страница {page}: всего {len(rows)}")
        page += 1

        if "next" not in data:
            break
        start = data["next"]
        time.sleep(0.3)

    df = pd.DataFrame(rows)
    df.to_excel(out_path, index=False)
    print(f"сохранено: {out_path}  ({len(df)} строк)")
    return df
