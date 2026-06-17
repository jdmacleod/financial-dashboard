from datetime import date

from app.services.report import _month_ends, _period_key


def test_month_ends_single_month() -> None:
    assert _month_ends(date(2025, 1, 1), date(2025, 1, 31)) == [date(2025, 1, 31)]


def test_month_ends_spans_year_boundary() -> None:
    result = _month_ends(date(2024, 11, 15), date(2025, 1, 10))
    assert result == [date(2024, 11, 30), date(2024, 12, 31), date(2025, 1, 31)]


def test_month_ends_handles_february_leap_year() -> None:
    result = _month_ends(date(2024, 2, 1), date(2024, 2, 28))
    assert result == [date(2024, 2, 29)]


def test_month_ends_empty_when_from_after_to() -> None:
    assert _month_ends(date(2025, 5, 1), date(2025, 1, 1)) == []


def test_period_key_pads_single_digit_month() -> None:
    assert _period_key(date(2025, 3, 5)) == "2025-03"


def test_period_key_double_digit_month() -> None:
    assert _period_key(date(2025, 11, 1)) == "2025-11"
