"""Подготовка данных: производные поля и проверка заполненности."""

import numpy as np
import pandas as pd

from .config import (
    CALL_SOURCES,
    CSV_COLUMNS,
    NEW_PIPELINE,
    STUCK_STAGES,
    WHATSAPP_PATTERNS,
    WON_STAGES,
)


def resolve_stages(stage: pd.Series, configured: list[str], suffix: str) -> list[str]:
    """Возвращает стадии из config, а если список пуст — найденные автоматически.

    Автоматически берётся стадия, равная suffix ("NEW") или оканчивающаяся
    на ":" + suffix ("C15:NEW"). Пользовательские стадии вроде UC_RENEW
    не подходят, хотя тоже заканчиваются на NEW.
    """
    if configured:
        return list(configured)
    return sorted(s for s in stage.unique() if s == suffix or s.endswith(":" + suffix))


def _read_csv(path: str) -> pd.DataFrame:
    """Читает CSV в UTF-8 или Windows-1251, с разделителем "," или ";".

    Разделитель определяется по строке заголовков: какого символа там больше.
    """
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            with open(path, encoding=encoding) as f:
                header = f.readline()
            sep = ";" if header.count(";") > header.count(",") else ","
            return pd.read_csv(path, sep=sep, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{path}: кодировка не UTF-8 и не Windows-1251")


def _to_number(s: pd.Series) -> pd.Series:
    """Превращает суммы вида "1 500 000,50" в числа; нечисловое — в NaN."""
    if pd.api.types.is_numeric_dtype(s):
        return s
    cleaned = s.astype(str).str.replace(r"\s", "", regex=True).str.replace(",", ".")
    return pd.to_numeric(cleaned, errors="coerce")


def load(path: str) -> pd.DataFrame:
    """Читает выгрузку (csv или xlsx) и приводит её к единому виду.

    Русские названия колонок из интерфейса Битрикс24 переименовываются
    в коды API (см. CSV_COLUMNS), суммы превращаются в числа.
    """
    df = _read_csv(path) if path.endswith(".csv") else pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns=CSV_COLUMNS)
    if "OPPORTUNITY" in df:
        df["OPPORTUNITY"] = _to_number(df["OPPORTUNITY"])
    return df


def _to_datetime(s: pd.Series) -> pd.Series:
    """Даты из API ("2024-05-01T10:00:00+03:00") и из интерфейса ("01.05.2024 10:00:00")."""
    try:
        return pd.to_datetime(s, format="ISO8601", utc=True)
    except ValueError:
        return pd.to_datetime(s, dayfirst=True, utc=True)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет производные колонки: канал, воронку, флаги стадий, лаг.

    Возвращает копию исходного DataFrame с колонками:
    created, modified, lag_hours, channel, pipeline, is_stuck, is_won.
    Колонка не создаётся, если в данных нет исходной колонки для неё.
    """
    df = df.copy()
    if "DATE_CREATE" in df:
        df["created"] = _to_datetime(df["DATE_CREATE"])
    if "DATE_MODIFY" in df:
        df["modified"] = _to_datetime(df["DATE_MODIFY"])

    if "created" in df and "modified" in df:
        # ВАЖНО: это НЕ время ответа. DATE_MODIFY — последнее изменение,
        # а не первое касание. Значение годится только как верхняя оценка.
        df["lag_hours"] = (df["modified"] - df["created"]).dt.total_seconds() / 3600

    if "SOURCE_ID" in df:
        src = df["SOURCE_ID"].astype(str)
        df["channel"] = np.select(
            [src.str.contains(WHATSAPP_PATTERNS, na=False, regex=True),
             df["SOURCE_ID"].isin(CALL_SOURCES)],
            ["WhatsApp", "Звонок"],
            default="Прочее",
        )

    if "STAGE_ID" in df:
        stage = df["STAGE_ID"].astype(str)
        df["pipeline"] = np.where(
            stage.str.startswith(f"{NEW_PIPELINE}:"), f"новая ({NEW_PIPELINE})", "старая"
        )
        df["is_stuck"] = stage.isin(resolve_stages(stage, STUCK_STAGES, "NEW"))
        df["is_won"] = stage.isin(resolve_stages(stage, WON_STAGES, "WON"))
    return df


def field_coverage(df: pd.DataFrame) -> None:
    """Печатает заполненность полей. Проверять ДО того, как строить на поле выводы."""
    print("\n" + "=" * 60)
    print("ЗАПОЛНЕННОСТЬ ПОЛЕЙ")
    print("=" * 60)
    for col in ("SOURCE_ID", "OPPORTUNITY", "ASSIGNED_BY_ID"):
        if col not in df:
            continue
        filled = df[col].notna()
        if col == "OPPORTUNITY":
            filled &= df[col].fillna(0) > 0
        print(f"{col:<18} {filled.sum():>6} / {len(df)}  ({filled.mean() * 100:.1f}%)")
    print("\nЕсли заполненность ниже ~50% — на поле нельзя строить выводы.")
