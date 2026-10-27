"""Страница report.html: главная цифра, светофор показателей, блок «Что исправить».

Простой HTML без внешних библиотек: открывается в любом браузере
и печатается на одну страницу. Только агрегаты — без строк, имён и ID.
"""

import html

import pandas as pd

from .config import CLIENT_TZ, REPORT_HTML, TRAFFIC_LIGHTS, WORK_END, WORK_START
from .reports import work_period

# Цвет светофора -> (цвет на странице, подпись словом — для тех, кто плохо различает цвета).
COLORS = {
    "green": ("#1e8e3e", "норма"),
    "yellow": ("#e8a200", "внимание"),
    "red": ("#d93025", "плохо"),
    "grey": ("#9aa0a6", "нет данных"),
}

# Показатели светофора: ключ из TRAFFIC_LIGHTS -> (подпись, единица измерения).
LIGHTS = {
    "whatsapp_stuck": ("Необработано WhatsApp-заявок", "%"),
    "offhours_stuck": ("Необработано заявок вне рабочего времени и в выходные", "%"),
    "stuck_age_days": ("Медианный возраст необработанной заявки", " дн."),
    "never_opened": ("Заявки, которые ни разу не открывали", "%"),
    "conversion": ("Конверсия в выигранные сделки", "%"),
}

CSS = """
* { box-sizing: border-box; }
body { margin: 0; background: #f4f5f7; color: #202124;
       font: 16px/1.45 -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 32px 16px; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 0 0 12px; }
.meta, .hint, footer { color: #5f6368; font-size: 14px; }
section { background: #fff; border-radius: 12px; padding: 20px 24px; margin-top: 16px; }
.hero { display: flex; align-items: center; gap: 24px; border-left: 10px solid var(--c); }
.big { font-size: 72px; font-weight: 700; line-height: 1; color: var(--c); }
.lights { width: 100%; border-collapse: collapse; }
.lights td { padding: 10px 8px; border-top: 1px solid #e8eaed; vertical-align: middle; }
.lights tr:first-child td { border-top: 0; }
.dot { display: inline-block; width: 18px; height: 18px; border-radius: 50%; }
.val { font-weight: 700; white-space: nowrap; text-align: right; }
.word { white-space: nowrap; color: #5f6368; }
.todo ol { min-height: 120px; margin: 0; padding-left: 24px; outline: none; }
.todo li { border-bottom: 1px solid #dadce0; min-height: 36px; }
footer { margin-top: 16px; }
@media print { body { background: #fff; } main { padding: 0; } section { padding: 12px 0; } }
@page { size: A4; margin: 15mm; }
"""


def _pct(flags: pd.Series) -> float | None:
    """Доля True в колонке, в процентах. None — если строк нет."""
    return float(flags.mean() * 100) if len(flags) else None


def _light(value: float | None, yellow: float, red: float) -> str:
    """Цвет светофора по порогам (как читать пороги — см. TRAFFIC_LIGHTS в config)."""
    if value is None or pd.isna(value):
        return "grey"
    if yellow <= red:  # «меньше — лучше»
        if value >= red:
            return "red"
        if value >= yellow:
            return "yellow"
        return "green"
    # «больше — лучше»
    if value <= red:
        return "red"
    if value <= yellow:
        return "yellow"
    return "green"


def _hint(key: str, unit: str) -> str:
    """Подсказка с порогами под показателем, например «зелёный < 10%, красный ≥ 25%»."""
    yellow, red = TRAFFIC_LIGHTS[key]
    if yellow <= red:
        return f"зелёный &lt; {yellow}{unit}, красный ≥ {red}{unit}"
    return f"зелёный &gt; {yellow}{unit}, красный ≤ {red}{unit}"


def compute_metrics(df: pd.DataFrame) -> dict[str, float | None]:
    """Считает показатели страницы. Если для показателя нет данных — None."""
    m = dict.fromkeys(TRAFFIC_LIGHTS)  # сначала у всех «нет данных»
    if "is_stuck" in df:
        m["stuck_share"] = _pct(df["is_stuck"])
        if "channel" in df:
            m["whatsapp_stuck"] = _pct(df.loc[df["channel"] == "WhatsApp", "is_stuck"])
        if "created" in df:
            off = work_period(df) != "Будни, рабочее время"
            m["offhours_stuck"] = _pct(df.loc[off, "is_stuck"])
        if "created" in df and "modified" in df and df["is_stuck"].any():
            age = (df["modified"].max() - df.loc[df["is_stuck"], "created"]).dt.days
            m["stuck_age_days"] = float(age.median())
    if "lag_hours" in df:
        m["never_opened"] = _pct(df["lag_hours"] < 0.017)  # меньше минуты, как в report_lag
    if "is_won" in df:
        m["conversion"] = _pct(df["is_won"])
    return m


def save_html_report(df: pd.DataFrame, path: str = REPORT_HTML) -> None:
    """Сохраняет одностраничный report.html с итогами анализа."""
    m = compute_metrics(df)

    meta = [f"сделок: {len(df)}"]
    if "created" in df:
        meta.insert(0, f"период: {df['created'].min().date()} — {df['created'].max().date()}")
    if "modified" in df:
        meta.append(f"срез на {df['modified'].max().date()}")

    share = m["stuck_share"]
    color, word = COLORS[_light(share, *TRAFFIC_LIGHTS["stuck_share"])]
    if share is None:
        big, caption = "—", "нет данных о стадиях сделок"
    else:
        n = int(df["is_stuck"].sum())
        big, caption = f"{share:.0f}%", f"заявок так и не обработаны ({n} из {len(df)})"

    rows = []
    for key, (label, unit) in LIGHTS.items():
        value = m[key]
        c, w = COLORS[_light(value, *TRAFFIC_LIGHTS[key])]
        if value is None:
            shown = "—"
        elif unit == " дн.":
            shown = f"{value:.0f}{unit}"
        else:
            shown = f"{value:.1f}{unit}"
        rows.append(
            f'<tr><td><span class="dot" style="background:{c}"></span></td>'
            f'<td>{label}<div class="hint">{_hint(key, unit)}</div></td>'
            f'<td class="val">{shown}</td><td class="word">{w}</td></tr>'
        )

    hours = html.escape(f"{WORK_START}–{WORK_END}, {CLIENT_TZ}")
    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Обработка заявок — итоги</title>
<style>{CSS}</style>
</head>
<body>
<main>
  <h1>Обработка входящих заявок</h1>
  <p class="meta">{html.escape(" · ".join(meta))}</p>

  <section class="hero" style="--c: {color}">
    <div class="big">{big}</div>
    <div>{caption}<div class="hint">оценка: {word}</div></div>
  </section>

  <section>
    <h2>Светофор</h2>
    <table class="lights">
      {"".join(rows)}
    </table>
  </section>

  <section class="todo">
    <h2>Что исправить</h2>
    <p class="hint">Заполняется после разговора с владельцем.</p>
    <!-- Впиши пункты сюда: по одному на <li>. -->
    <ol contenteditable="true"><li></li><li></li><li></li></ol>
  </section>

  <footer>Данные обезличены: только доли и количества, без имён и контактов.
  Рабочее время: {hours}. Пороги светофора — TRAFFIC_LIGHTS в config.py.</footer>
</main>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"\nСтраница с итогами сохранена: {path}")
