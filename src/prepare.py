"""Подготовка данных: производные поля и проверка заполненности."""

import numpy as np
import pandas as pd

from .config import (
    CALL_SOURCES,
    NEW_PIPELINE,
    STUCK_STAGES,
    WHATSAPP_PATTERNS,
    WON_STAGES,
)


def resolve_stages(stage: pd.Series, configured: list[str], suffix: str) -> list[str]:
    """Возвращает стадии из config, а если список пуст — все стадии на suffix."""
    if configured:
        return list(configured)
    return sorted(s for s in stage.unique() if s.endswith(suffix))


def load(path: str) -> pd.DataFrame:
    """Читает выгрузку из csv или xlsx по расширению файла."""
    if path.endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет производные колонки: канал, воронку, флаги стадий, лаг.

    Возвращает копию исходного DataFrame с колонками:
    created, modified, lag_hours, channel, pipeline, is_stuck, is_won.
    """
    df = df.copy()
    df["created"] = pd.to_datetime(df["DATE_CREATE"], format="ISO8601", utc=True)
    df["modified"] = pd.to_datetime(df["DATE_MODIFY"], format="ISO8601", utc=True)

    # ВАЖНО: это НЕ время ответа. DATE_MODIFY — последнее изменение,
    # а не первое касание. Значение годится только как верхняя оценка.
    df["lag_hours"] = (df["modified"] - df["created"]).dt.total_seconds() / 3600

    src = df["SOURCE_ID"].astype(str)
    df["channel"] = np.select(
        [src.str.contains(WHATSAPP_PATTERNS, na=False, regex=True),
         df["SOURCE_ID"].isin(CALL_SOURCES)],
        ["WhatsApp", "Звонок"],
        default="Прочее",
    )

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
