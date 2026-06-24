"""Pure unit tests for age.py — no database required."""

from __future__ import annotations

from datetime import date

from app.services.age import age_in_year, current_age, rmd_start_age, year_turning_age


class TestCurrentAge:
    def test_none_dob_returns_none(self) -> None:
        assert current_age(None) is None

    def test_birthday_already_passed_this_year(self) -> None:
        assert current_age(date(1990, 1, 1), as_of=date(2024, 6, 1)) == 34

    def test_birthday_not_yet_this_year(self) -> None:
        assert current_age(date(1990, 12, 31), as_of=date(2024, 6, 1)) == 33

    def test_birthday_exactly_today_counts(self) -> None:
        assert current_age(date(1990, 6, 1), as_of=date(2024, 6, 1)) == 34

    def test_day_before_birthday_does_not_count(self) -> None:
        assert current_age(date(1990, 6, 2), as_of=date(2024, 6, 1)) == 33

    def test_leap_day_birth_before_feb29_in_common_year(self) -> None:
        # Born Feb 29; as of Feb 28 2025 (common year) the birthday hasn't
        # "occurred" yet, so they're still the younger age.
        assert current_age(date(2000, 2, 29), as_of=date(2025, 2, 28)) == 24

    def test_leap_day_birth_on_mar1_common_year(self) -> None:
        assert current_age(date(2000, 2, 29), as_of=date(2025, 3, 1)) == 25


class TestAgeInYear:
    def test_none_dob_returns_none(self) -> None:
        assert age_in_year(None, 2030) is None

    def test_age_reached_during_year(self) -> None:
        assert age_in_year(date(1980, 7, 15), 2030) == 50


class TestYearTurningAge:
    def test_none_dob_returns_none(self) -> None:
        assert year_turning_age(None, 65) is None

    def test_year_member_turns_age(self) -> None:
        assert year_turning_age(date(1965, 3, 10), 75) == 2040


class TestRmdStartAge:
    def test_none_dob_returns_none(self) -> None:
        assert rmd_start_age(None) is None

    def test_born_1950_or_earlier_is_72(self) -> None:
        assert rmd_start_age(date(1950, 12, 31)) == 72
        assert rmd_start_age(date(1945, 1, 1)) == 72

    def test_born_1951_to_1959_is_73(self) -> None:
        assert rmd_start_age(date(1951, 1, 1)) == 73
        assert rmd_start_age(date(1959, 12, 31)) == 73

    def test_born_1960_or_later_is_75(self) -> None:
        assert rmd_start_age(date(1960, 1, 1)) == 75
        assert rmd_start_age(date(1985, 6, 15)) == 75
