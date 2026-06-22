"""Unit tests for seed_households._util pure-function helpers.

Only stdlib-pure helpers are tested here (third_wednesday, DATE_END default).
DB-dependent functions (make_household, seed, build_snapshots, etc.) require a
real AsyncSession and are exercised end-to-end by running the seed script.

Coverage note: scripts/ is excluded from [tool.coverage.run] source = ["app"],
so these tests do not contribute to the measured coverage percentage. They exist
to catch regressions in the date-math logic shared by all five seed modules.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

# backend/scripts/ must be on sys.path for seed_households to be importable
_SCRIPTS_DIR = str(Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from seed_households import _util  # noqa: E402


class TestThirdWednesday:
    def test_january_2024(self) -> None:
        # Jan 1 2024 is Monday; days_until_wed=(2-0)%7=2 → first Wed Jan 3 → 3rd Wed Jan 17
        assert _util.third_wednesday(2024, 1) == date(2024, 1, 17)

    def test_month_starting_on_wednesday(self) -> None:
        # May 1 2024 is Wednesday; days_until_wed=(2-2)%7=0 → first Wed May 1 → 3rd Wed May 15
        assert _util.third_wednesday(2024, 5) == date(2024, 5, 15)

    def test_result_is_always_wednesday(self) -> None:
        for year in (2024, 2025):
            for month in range(1, 13):
                d = _util.third_wednesday(year, month)
                assert d.weekday() == 2, f"{year}-{month:02d}: {d} is not a Wednesday"

    def test_clamps_to_date_end(self) -> None:
        # Patch DATE_END to Mar 1 2024; Mar 2024's 3rd Wed is Mar 20, which exceeds it.
        with patch.object(_util, "DATE_END", date(2024, 3, 1)):
            result = _util.third_wednesday(2024, 3)
        assert result == date(2024, 3, 1)


@pytest.mark.skipif(
    os.getenv("SEED_DATE_END") is not None,
    reason="SEED_DATE_END is set in the environment; default-value test is not applicable",
)
def test_date_end_default_value() -> None:
    """DATE_END is 2026-06-21 when SEED_DATE_END is not set."""
    assert date(2026, 6, 21) == _util.DATE_END


class TestJitter:
    def test_result_within_range(self) -> None:
        from decimal import Decimal
        import random

        rng = random.Random(42)
        amount = Decimal("100.00")
        for _ in range(50):
            result = _util.jitter(amount, rng, pct=0.10)
            assert Decimal("90.00") <= result <= Decimal("110.00")

    def test_result_quantized_to_cents(self) -> None:
        from decimal import Decimal
        import random

        rng = random.Random(1)
        result = _util.jitter(Decimal("99.99"), rng, pct=0.05)
        assert result == result.quantize(Decimal("0.01"))

    def test_zero_pct_returns_original(self) -> None:
        from decimal import Decimal
        import random

        rng = random.Random(7)
        result = _util.jitter(Decimal("50.00"), rng, pct=0.0)
        assert result == Decimal("50.00")


class TestClampDay:
    def test_normal_day_unchanged(self) -> None:
        assert _util.clamp_day(2024, 3, 15) == date(2024, 3, 15)

    def test_clamps_to_last_day_of_month(self) -> None:
        # February 2024 has 29 days (leap year); day 31 should clamp to 29
        assert _util.clamp_day(2024, 2, 31) == date(2024, 2, 29)

    def test_clamps_to_date_end(self) -> None:
        with patch.object(_util, "DATE_END", date(2024, 6, 10)):
            result = _util.clamp_day(2024, 6, 28)
        assert result == date(2024, 6, 10)

    def test_no_clamp_needed(self) -> None:
        # Day 1 of any month is always valid and before DATE_END
        assert _util.clamp_day(2024, 1, 1) == date(2024, 1, 1)


class TestGenVariable:
    def _account_id(self):
        import uuid
        return uuid.uuid4()

    def test_count_zero_returns_empty(self) -> None:
        import random

        rng = random.Random(0)
        from decimal import Decimal

        result = _util.gen_variable(
            self._account_id(), 2024, 3, None,
            ["Shop"], Decimal("50.00"), Decimal("100.00"),
            0, 0, rng,
        )
        assert result == []

    def test_single_transaction_correct_sign(self) -> None:
        import random
        from decimal import Decimal

        rng = random.Random(42)
        result = _util.gen_variable(
            self._account_id(), 2024, 3, None,
            ["Costco"], Decimal("100.00"), Decimal("200.00"),
            1, 1, rng,
        )
        assert len(result) == 1
        assert result[0].amount < Decimal("0")

    def test_sum_invariant_single_transaction(self) -> None:
        import random
        from decimal import Decimal

        rng = random.Random(99)
        result = _util.gen_variable(
            self._account_id(), 2024, 5, None,
            ["Walmart"], Decimal("50.00"), Decimal("50.00"),
            1, 1, rng,
        )
        # With min==max the midpoint is 50, jittered by 12% → between 44 and 56
        assert len(result) == 1
        assert Decimal("44.00") <= abs(result[0].amount) <= Decimal("56.00")

    def test_multi_transaction_amounts_positive_and_in_month(self) -> None:
        import random
        from decimal import Decimal

        rng = random.Random(7)
        result = _util.gen_variable(
            self._account_id(), 2024, 6, None,
            ["A", "B", "C"], Decimal("100.00"), Decimal("200.00"),
            3, 3, rng,
        )
        assert len(result) == 3
        for t in result:
            assert t.amount < Decimal("0"), "all transactions should be expenses (negative)"
            assert t.transaction_date.year == 2024
            assert t.transaction_date.month == 6

    def test_payees_drawn_from_merchant_list(self) -> None:
        import random
        from decimal import Decimal

        merchants = ["MerchantX", "MerchantY"]
        rng = random.Random(13)
        result = _util.gen_variable(
            self._account_id(), 2024, 4, None,
            merchants, Decimal("80.00"), Decimal("120.00"),
            4, 4, rng,
        )
        for t in result:
            assert t.payee_raw in merchants


class TestLastDayOf:
    def test_february_leap_year(self) -> None:
        assert _util.last_day_of(2024, 2) == date(2024, 2, 29)

    def test_february_non_leap_year(self) -> None:
        assert _util.last_day_of(2025, 2) == date(2025, 2, 28)

    def test_thirty_one_day_month(self) -> None:
        assert _util.last_day_of(2024, 1) == date(2024, 1, 31)

    def test_thirty_day_month(self) -> None:
        assert _util.last_day_of(2024, 4) == date(2024, 4, 30)


class TestAllMonths:
    def test_first_element_is_jan_2024(self) -> None:
        months = _util.all_months()
        assert months[0] == date(2024, 1, 1)

    def test_all_elements_are_first_of_month(self) -> None:
        for d in _util.all_months():
            assert d.day == 1

    def test_sequential_months(self) -> None:
        months = _util.all_months()
        for i in range(1, len(months)):
            prev, curr = months[i - 1], months[i]
            # consecutive months: either same year +1 month, or year +1 with month=1
            assert (curr.year == prev.year and curr.month == prev.month + 1) or (
                curr.year == prev.year + 1 and curr.month == 1 and prev.month == 12
            )


class TestFridayDates:
    def test_all_results_are_fridays(self) -> None:
        for d in _util.friday_dates(2024, 3):
            assert d.weekday() == 4, f"{d} is not a Friday"

    def test_march_2024_has_five_fridays(self) -> None:
        # March 2024: Fridays are 1, 8, 15, 22, 29
        fridays = _util.friday_dates(2024, 3)
        assert len(fridays) == 5

    def test_april_2024_has_four_fridays(self) -> None:
        fridays = _util.friday_dates(2024, 4)
        assert len(fridays) == 4


class TestRandDate:
    def test_result_in_given_month(self) -> None:
        import random

        rng = random.Random(5)
        for _ in range(20):
            d = _util.rand_date(2024, 6, rng)
            assert d.year == 2024 and d.month == 6

    def test_avoid_sunday_never_returns_sunday(self) -> None:
        import random

        rng = random.Random(99)
        for _ in range(50):
            d = _util.rand_date(2024, 3, rng, avoid_sunday=True)
            assert d.weekday() != 6, f"{d} is a Sunday but avoid_sunday=True"


class TestSplit:
    def test_count_one_returns_list_of_total(self) -> None:
        import random
        from decimal import Decimal

        from seed_households import h5_langford

        rng = random.Random(0)
        result = h5_langford._split(Decimal("100.00"), 1, rng)
        assert result == [Decimal("100.00")]

    def test_parts_sum_to_total_count_two(self) -> None:
        import random
        from decimal import Decimal

        from seed_households import h5_langford

        total = Decimal("100.00")
        parts = h5_langford._split(total, 2, random.Random(42))
        assert sum(parts) == total

    def test_parts_sum_to_total_count_three(self) -> None:
        import random
        from decimal import Decimal

        from seed_households import h5_langford

        total = Decimal("300.00")
        parts = h5_langford._split(total, 3, random.Random(7))
        assert sum(parts) == total

    def test_all_parts_positive(self) -> None:
        import random
        from decimal import Decimal

        from seed_households import h5_langford

        parts = h5_langford._split(Decimal("50.00"), 4, random.Random(99))
        for p in parts:
            assert p > Decimal("0")
