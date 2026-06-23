"""Unit tests for the defined-benefit pension present-value model."""

from datetime import date
from decimal import Decimal

from app.db.models.pension import PensionAccount, PensionEstimateHistory
from app.services.pension_valuation import (
    PENSION_DISCOUNT_RATE,
    effective_estimate,
    pension_present_value,
    pension_value_at,
)

AS_OF = date(2025, 1, 1)


def _hist(effective_date: date, monthly: Decimal) -> PensionEstimateHistory:
    """A transient estimate-history row for formula/selection testing."""
    return PensionEstimateHistory(
        effective_date=effective_date,
        monthly_benefit_estimate=monthly,
        cola_adjustment_rate=Decimal("0.02"),
        survivor_benefit_percent=None,
        eligibility_date=None,
    )


def _pension(
    monthly: Decimal | None,
    *,
    cola: Decimal = Decimal("0.02"),
    eligibility_date: date | None = None,
    survivor: Decimal | None = None,
) -> PensionAccount:
    """A transient (unpersisted) PensionAccount for formula testing."""
    return PensionAccount(
        monthly_benefit_estimate=monthly,
        cola_adjustment_rate=cola,
        eligibility_date=eligibility_date,
        survivor_benefit_percent=survivor,
    )


def test_none_pension_is_zero() -> None:
    assert pension_present_value(None, AS_OF) == Decimal("0")


def test_no_estimate_is_zero() -> None:
    assert pension_present_value(_pension(None), AS_OF) == Decimal("0")
    assert pension_present_value(_pension(Decimal("0")), AS_OF) == Decimal("0")


def test_finite_annuity_is_less_than_perpetuity() -> None:
    """A finite life annuity is worth strictly less than the old perpetuity."""
    monthly = Decimal("3000.00")
    pv = pension_present_value(_pension(monthly), AS_OF)
    perpetuity = monthly * 12 / PENSION_DISCOUNT_RATE
    assert pv > 0
    assert pv < perpetuity


def test_deferred_benefit_worth_less_than_in_pay() -> None:
    """A benefit that does not start for 20 years is worth less today than the
    same benefit already in payment."""
    monthly = Decimal("3000.00")
    in_pay = pension_present_value(_pension(monthly), AS_OF)
    deferred = pension_present_value(_pension(monthly, eligibility_date=date(2045, 1, 1)), AS_OF)
    assert deferred < in_pay


def test_past_eligibility_date_is_not_discounted() -> None:
    """An eligibility date in the past is treated as in-payment (no extra discount)."""
    monthly = Decimal("3000.00")
    in_pay = pension_present_value(_pension(monthly), AS_OF)
    past = pension_present_value(_pension(monthly, eligibility_date=date(2010, 1, 1)), AS_OF)
    assert past == in_pay


def test_survivor_benefit_increases_value() -> None:
    monthly = Decimal("3000.00")
    without = pension_present_value(_pension(monthly), AS_OF)
    with_survivor = pension_present_value(_pension(monthly, survivor=Decimal("0.50")), AS_OF)
    assert with_survivor > without


def test_higher_cola_increases_value() -> None:
    monthly = Decimal("3000.00")
    low = pension_present_value(_pension(monthly, cola=Decimal("0.01")), AS_OF)
    high = pension_present_value(_pension(monthly, cola=Decimal("0.03")), AS_OF)
    assert high > low


def test_cola_equal_to_discount_rate_is_finite_and_positive() -> None:
    """The rate == growth degenerate branch must not divide by zero."""
    pv = pension_present_value(_pension(Decimal("3000.00"), cola=PENSION_DISCOUNT_RATE), AS_OF)
    assert pv > 0


# --- Estimate history selection --------------------------------------------

_H1 = _hist(date(2024, 1, 1), Decimal("2000"))
_H2 = _hist(date(2025, 6, 1), Decimal("2500"))
_HISTORY = [_H1, _H2]  # sorted oldest-first


def test_effective_estimate_empty_is_none() -> None:
    assert effective_estimate([], date(2025, 1, 1)) is None


def test_effective_estimate_before_first_uses_earliest() -> None:
    # A date before any recorded estimate uses the inception estimate.
    assert effective_estimate(_HISTORY, date(2023, 1, 1)) is _H1


def test_effective_estimate_picks_latest_on_or_before() -> None:
    assert effective_estimate(_HISTORY, date(2025, 1, 1)) is _H1
    assert effective_estimate(_HISTORY, date(2025, 6, 1)) is _H2
    assert effective_estimate(_HISTORY, date(2026, 1, 1)) is _H2


def test_pension_value_at_uses_effective_estimate() -> None:
    # Before the bump, the value reflects the $2000 estimate; after, $2500.
    early = pension_value_at(None, _HISTORY, date(2025, 1, 1))
    late = pension_value_at(None, _HISTORY, date(2025, 12, 1))
    assert early == pension_present_value(_H1, date(2025, 1, 1))
    assert late == pension_present_value(_H2, date(2025, 12, 1))
    assert late > early


def test_pension_value_at_falls_back_to_pension_without_history() -> None:
    pension = _pension(Decimal("3000"))
    assert pension_value_at(pension, [], AS_OF) == pension_present_value(pension, AS_OF)


def test_pension_value_at_none_pension_no_history_is_zero() -> None:
    assert pension_value_at(None, [], AS_OF) == Decimal("0")
