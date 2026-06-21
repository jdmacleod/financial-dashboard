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
    assert _util.DATE_END == date(2026, 6, 21)
