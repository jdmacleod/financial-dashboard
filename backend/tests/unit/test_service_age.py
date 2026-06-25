"""Pure unit tests for age.py — no database required."""

from __future__ import annotations

from datetime import date

from app.services.age import (
    age_in_year,
    current_age,
    full_retirement_age_months,
    milestones,
    rmd_start_age,
    year_turning_age,
)


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


class TestFullRetirementAge:
    def test_none_dob_returns_none(self) -> None:
        assert full_retirement_age_months(None) is None

    def test_1937_or_earlier_is_65(self) -> None:
        assert full_retirement_age_months(date(1937, 1, 1)) == 65 * 12

    def test_1943_to_1954_is_66(self) -> None:
        assert full_retirement_age_months(date(1950, 1, 1)) == 66 * 12

    def test_1955_steps_up_two_months(self) -> None:
        assert full_retirement_age_months(date(1955, 1, 1)) == 66 * 12 + 2

    def test_1960_or_later_is_67(self) -> None:
        assert full_retirement_age_months(date(1960, 1, 1)) == 67 * 12
        assert full_retirement_age_months(date(1990, 1, 1)) == 67 * 12


class TestMilestones:
    def test_none_dob_returns_none(self) -> None:
        assert milestones(None) is None

    def test_ordered_keys_and_years(self) -> None:
        ms = milestones(date(1990, 6, 15))
        assert ms is not None
        assert [m.key for m in ms] == [
            "early_withdrawal",
            "social_security_earliest",
            "medicare",
            "full_retirement_age",
            "rmd",
        ]
        assert [m.year for m in ms] == [2049, 2052, 2055, 2057, 2065]

    def test_full_retirement_age_label_for_1955(self) -> None:
        ms = milestones(date(1955, 3, 1))
        assert ms is not None
        fra = next(m for m in ms if m.key == "full_retirement_age")
        assert fra.age_label == "66y 2m"

    def test_59_and_a_half_crosses_year_boundary(self) -> None:
        # Born October -> age 59½ falls the following calendar year.
        ms = milestones(date(2000, 10, 1))
        assert ms is not None
        early = next(m for m in ms if m.key == "early_withdrawal")
        assert early.date == date(2060, 4, 1)
        assert early.year == 2060

    def test_no_retirement_target_milestone_when_unset(self) -> None:
        ms = milestones(date(1990, 6, 15))
        assert ms is not None
        assert all(m.key != "retirement_target" for m in ms)

    def test_retirement_target_milestone_added_and_ordered(self) -> None:
        ms = milestones(date(1990, 6, 15), retirement_target_age=60)
        assert ms is not None
        target = next(m for m in ms if m.key == "retirement_target")
        assert target.label == "Target retirement"
        assert target.age_label == "60"
        assert target.year == 2050
        assert target.date == date(2050, 6, 15)
        # Sorted by date: target (60) sits after early_withdrawal (59½) and
        # before social_security_earliest (62).
        keys = [m.key for m in ms]
        assert keys.index("retirement_target") == keys.index("early_withdrawal") + 1
        assert keys.index("retirement_target") < keys.index("social_security_earliest")
