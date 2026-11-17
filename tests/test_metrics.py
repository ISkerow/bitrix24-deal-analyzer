"""Тесты расчётов: правило 24 часов, медианный возраст застрявших, рабочее время."""

import pandas as pd

from src.html_report import compute_metrics
from src.prepare import prepare
from src.reports import work_period

# Дата среза: самая поздняя DATE_MODIFY в данных (понедельник, 12:00 по Алматы).
REF = pd.Timestamp("2026-10-26 12:00", tz="Asia/Almaty")


def make_deals(rows: list[tuple[str, float]]) -> pd.DataFrame:
    """Сделки из пар (стадия, сколько часов назад создана) относительно REF.

    У всех сделок DATE_MODIFY = REF, поэтому срез — ровно REF.
    """
    created = [(REF - pd.Timedelta(hours=h)).isoformat() for _, h in rows]
    return prepare(pd.DataFrame({
        "ID": range(len(rows)),
        "STAGE_ID": [stage for stage, _ in rows],
        "SOURCE_ID": "WEB",
        "DATE_CREATE": created,
        "DATE_MODIFY": REF.isoformat(),
    }))


def test_stuck_only_after_24_hours():
    """«Новая» старше 24 ч — застряла; моложе или ровно 24 ч — ещё нет."""
    df = make_deals([("C15:NEW", 25), ("C15:NEW", 24), ("C15:NEW", 23)])

    assert df["is_stuck"].tolist() == [True, False, False]
    assert df["is_old_enough"].tolist() == [True, False, False]


def test_fresh_deals_are_not_in_stuck_share():
    """Свежие заявки не входят ни в застрявшие, ни в знаменатель доли."""
    df = make_deals([
        ("C15:NEW", 48),  # старая, застряла
        ("C15:WON", 48),  # старая, обработана
        ("C15:NEW", 2),   # свежая — не считается
        ("C15:WON", 2),   # свежая — не считается
    ])

    assert compute_metrics(df)["stuck_share"] == 50.0  # 1 из 2, а не 1 из 4


def test_stuck_age_is_median_in_days():
    """Медианный возраст застрявших: из 10, 20 и 40 дней — 20."""
    df = make_deals([("C15:NEW", 10 * 24), ("C15:NEW", 20 * 24), ("C15:NEW", 40 * 24)])

    assert compute_metrics(df)["stuck_age_days"] == 20.0


def test_no_stuck_age_without_stuck_deals():
    """Нет застрявших — нет и возраста: «нет данных», а не ноль."""
    df = make_deals([("C15:WON", 48)])

    assert compute_metrics(df)["stuck_age_days"] is None


def test_work_period_boundaries_in_client_timezone():
    """Рабочее время 09:00–18:00 по Алматы: начало входит, конец — нет."""
    times = [
        "2026-10-26T08:59:00+05:00",  # понедельник, до начала
        "2026-10-26T09:00:00+05:00",  # ровно начало
        "2026-10-26T17:59:00+05:00",  # последняя рабочая минута
        "2026-10-26T18:00:00+05:00",  # ровно конец
        "2026-10-26T04:00:00+00:00",  # 04:00 UTC = 09:00 по Алматы
        "2026-10-31T12:00:00+05:00",  # суббота, полдень
    ]
    df = prepare(pd.DataFrame({"DATE_CREATE": times, "DATE_MODIFY": times}))

    assert list(work_period(df)) == [
        "Будни, вне рабочего времени",
        "Будни, рабочее время",
        "Будни, рабочее время",
        "Будни, вне рабочего времени",
        "Будни, рабочее время",
        "Выходные",
    ]
