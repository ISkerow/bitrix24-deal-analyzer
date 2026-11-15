"""Тесты для _light: какой цвет светофора получает значение при заданных порогах."""

from src.html_report import _light


def test_lower_is_better_thresholds():
    """Пороги (10, 25), «меньше — лучше»: границы входят в худший цвет."""
    assert _light(9.9, 10, 25) == "green"
    assert _light(10, 10, 25) == "yellow"
    assert _light(24.9, 10, 25) == "yellow"
    assert _light(25, 10, 25) == "red"


def test_higher_is_better_thresholds():
    """Пороги (5, 2), «больше — лучше», как у конверсии."""
    assert _light(5.1, 5, 2) == "green"
    assert _light(5, 5, 2) == "yellow"
    assert _light(2, 5, 2) == "red"


def test_no_data_is_grey():
    """Нет значения (None или NaN) — серый, а не зелёный."""
    assert _light(None, 10, 25) == "grey"
    assert _light(float("nan"), 10, 25) == "grey"
