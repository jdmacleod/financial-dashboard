"""Unit tests for the Social Security claiming-age benefit adjustment."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.age import full_retirement_age_months
from app.services.social_security import (
    benefit_adjustment_factor,
    benefit_at_claiming_age,
    claiming_comparison,
)

# FRA 67 in months (born 1960+).
_FRA67 = 67 * 12  # 804


def test_factor_at_fra_is_one() -> None:
    assert benefit_adjustment_factor(_FRA67, _FRA67) == Decimal("1")


def test_factor_early_claim_at_62_with_fra_67() -> None:
    # 60 months early: 36 * 5/9% + 24 * 5/12% = 20% + 10% = 30% reduction -> 0.70.
    assert float(benefit_adjustment_factor(_FRA67, 62 * 12)) == pytest.approx(0.70)


def test_factor_delayed_claim_at_70_with_fra_67() -> None:
    # 36 months late: 36 * 2/3% = 24% credit -> 1.24.
    assert float(benefit_adjustment_factor(_FRA67, 70 * 12)) == pytest.approx(1.24)


def test_benefit_at_claiming_age_early_and_late() -> None:
    pia = Decimal("2000")
    assert benefit_at_claiming_age(pia, _FRA67, 62 * 12) == Decimal("1400.00")
    assert benefit_at_claiming_age(pia, _FRA67, _FRA67) == Decimal("2000.00")
    assert benefit_at_claiming_age(pia, _FRA67, 70 * 12) == Decimal("2480.00")


def test_claiming_comparison_fra_67() -> None:
    comp = claiming_comparison(Decimal("2000"), date(1960, 1, 1))
    assert comp.fra_months == 804
    assert len(comp.options) == 9  # ages 62..70 inclusive
    by_age = {o.claiming_age: o for o in comp.options}
    assert by_age[62].monthly_benefit == Decimal("1400.00")
    assert by_age[62].annual_benefit == Decimal("16800.00")
    assert by_age[67].is_fra is True
    assert by_age[67].monthly_benefit == Decimal("2000.00")
    assert by_age[70].monthly_benefit == Decimal("2480.00")
    assert by_age[70].pct_of_pia == pytest.approx(124.0)
    # Only the FRA age is flagged.
    assert sum(1 for o in comp.options if o.is_fra) == 1


def test_claiming_comparison_fra_66y2m_no_whole_age_is_fra() -> None:
    # Born 1955 -> FRA 66y2m = 794 months, which is not a whole claiming age.
    assert full_retirement_age_months(date(1955, 6, 1)) == 794
    comp = claiming_comparison(Decimal("2000"), date(1955, 6, 1))
    assert comp.fra_months == 794
    assert all(o.is_fra is False for o in comp.options)
    # 62 is 50 months early: 36*5/9% + 14*5/12% = 20% + 5.8333% = 25.8333% off.
    assert comp.options[0].claiming_age == 62
    assert comp.options[0].monthly_benefit == Decimal("1483.33")
