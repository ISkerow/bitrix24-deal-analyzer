"""Тесты для resolve_stages: какие стадии считаются «новыми» и «выигранными»."""

import pandas as pd

from src.prepare import resolve_stages


def test_configured_list_is_returned_as_is():
    """Если список в config задан — возвращается он, данные не важны."""
    stage = pd.Series(["NEW", "C15:NEW", "WON"])

    result = resolve_stages(stage, ["C15:NEW"], "NEW")

    assert result == ["C15:NEW"]


def test_empty_list_finds_new_stages_automatically():
    """Пустой список — находим "NEW" и "<воронка>:NEW" в данных."""
    stage = pd.Series(["NEW", "C15:NEW", "C15:WON", "LOSE"])

    result = resolve_stages(stage, [], "NEW")

    assert result == ["C15:NEW", "NEW"]  # функция возвращает отсортированный список


def test_custom_stage_ending_with_new_is_not_new():
    """UC_RENEW заканчивается на NEW, но новой стадией не является."""
    stage = pd.Series(["NEW", "UC_RENEW", "C15:UC_RENEW"])

    result = resolve_stages(stage, [], "NEW")

    assert result == ["NEW"]
