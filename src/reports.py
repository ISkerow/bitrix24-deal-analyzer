"""Отчёты по подготовленному DataFrame (см. prepare.prepare).

Каждый отчёт печатает свой блок и явно проговаривает ограничения
метрики, чтобы числа нельзя было прочитать сильнее, чем они есть.
"""

import pandas as pd

from .config import MIN_MONTH_DEALS


def report_pipelines(df: pd.DataFrame) -> None:
    """Размер и период каждой воронки; напоминает, что их нельзя смешивать."""
    print("\n" + "=" * 60)
    print("ВОРОНКИ")
    print("=" * 60)
    t = df.groupby("pipeline").agg(
        сделок=("ID", "size"),
        период_с=("created", lambda s: s.min().date()),
        период_по=("created", lambda s: s.max().date()),
    )
    print(t.to_string())
    print("\nСтарая и новая воронки несопоставимы — не смешивать в одном числе.")


def report_stuck(df: pd.DataFrame) -> None:
    """Сколько заявок застряло на стадии NEW и как давно они висят."""
    ref = df["modified"].max()  # точка отсчёта — из данных, не now()
    stuck = df[df["is_stuck"]]

    print("\n" + "=" * 60)
    print(f"НЕОБРАБОТАННЫЕ ЗАЯВКИ (стадия C15:NEW).  Срез на {ref.date()}")
    print("=" * 60)
    if stuck.empty:
        print("Застрявших заявок нет.")
        return
    print(f"Всего застряло: {len(stuck)} из {len(df)} ({len(stuck) / len(df) * 100:.1f}%)")

    age = (ref - stuck["created"]).dt.days
    print(f"Возраст заявки: медиана {age.median():.0f} дн, среднее {age.mean():.0f} дн")
    print("Это возраст необработанной заявки, а НЕ скорость ответа менеджера.")

    print("\nПо каналам:")
    ch = stuck["channel"].value_counts()
    for name, n in ch.items():
        print(f"  {name:<10} {n:>5}  ({n / len(stuck) * 100:.1f}%)")


def report_whatsapp_monthly(df: pd.DataFrame) -> None:
    """Главная таблица: доля застрявших WhatsApp-заявок по месяцам.

    Показывает срыв процесса: если в ранних месяцах канал работал,
    а в поздних доля необработанных растёт — проблема в объёме
    и процессе, а не в самом канале.
    """
    wa = df[df["channel"] == "WhatsApp"].copy()
    if wa.empty:
        print("\nWhatsApp-канал не найден — проверь WHATSAPP_PATTERNS")
        return

    wa["month"] = wa["created"].dt.strftime("%Y-%m")
    t = wa.groupby("month").agg(создано=("ID", "size"), застряло=("is_stuck", "sum"))
    t = t[t["создано"] >= MIN_MONTH_DEALS]  # шум отсекаем
    if t.empty:
        print(f"\nНет месяцев с {MIN_MONTH_DEALS}+ WhatsApp-заявками — таблица пропущена.")
        return
    t["доля_%"] = (t["застряло"] / t["создано"] * 100).round(0).astype(int)

    print("\n" + "=" * 60)
    print("WHATSAPP ПО МЕСЯЦАМ — ключевая таблица")
    print("=" * 60)
    print(t.to_string())

    bad = t[t["доля_%"] >= 50]
    if not bad.empty:
        print(f"\nМесяцев со срывом (>=50% необработано): {len(bad)}")
        print(f"Потеряно за этот период: {bad['застряло'].sum()} обращений")
        print("Сравни с ранними месяцами — там тот же канал работал нормально.")
        print("Значит проблема в объёме и процессе, а не в канале.")


def report_lag(df: pd.DataFrame) -> None:
    """Лаг создание→последнее изменение по каналам (верхняя оценка ответа)."""
    print("\n" + "=" * 60)
    print("ЛАГ ДО ПОСЛЕДНЕГО ИЗМЕНЕНИЯ (верхняя оценка времени ответа)")
    print("=" * 60)
    t = df.groupby("channel")["lag_hours"].agg(
        сделок="size",
        медиана_ч=lambda s: round(s.median(), 1),
        до_часа_pct=lambda s: round((s < 1).mean() * 100, 1),
        до_суток_pct=lambda s: round((s < 24).mean() * 100, 1),
    )
    print(t.to_string())

    never = (df["lag_hours"] < 0.017).sum()
    print(f"\nНи разу не открывали: {never} ({never / len(df) * 100:.1f}%)")
    print("Точное время ПЕРВОГО касания требует crm.activity.list — здесь его нет.")


def report_money(df: pd.DataFrame) -> None:
    """Оценка упущенных продаж: конверсия, средний чек, потери в деньгах."""
    won = df[df["is_won"]]
    stuck_n = int(df["is_stuck"].sum())
    conv = len(won) / len(df) if len(df) else 0

    print("\n" + "=" * 60)
    print("ОЦЕНКА ПОТЕРЬ")
    print("=" * 60)
    print(f"Выиграно сделок: {len(won)} из {len(df)} — конверсия {conv * 100:.2f}%")

    priced = won[won["OPPORTUNITY"].fillna(0) > 0]
    if len(priced) == 0:
        print("Суммы сделок не заполнены — средний чек берём у клиента.")
        return

    avg = priced["OPPORTUNITY"].mean()
    print(f"Средний чек: {avg:,.0f} (по {len(priced)} сделкам с суммой)")
    if len(priced) < 30:
        print("  ВНИМАНИЕ: выборка мала. В презентации указывать эту оговорку.")

    lost_deals = stuck_n * conv
    print(f"\nПотенциально упущено: {lost_deals:.0f} продаж")
    print(f"В деньгах (оценка): {lost_deals * avg:,.0f}")
    print("Показывать клиенту с его собственной маржой, а не с этой.")
