"""Pure unit tests for debt_projector.py — no database required."""

from __future__ import annotations

import math
from decimal import Decimal
from uuid import uuid4

from app.services.debt_projector import DebtRecord, project_payoff


def _debt(
    balance: str,
    rate: str,
    minimum: str,
    nickname: str = "Loan",
) -> DebtRecord:
    return DebtRecord(
        id=uuid4(),
        nickname=nickname,
        current_balance=Decimal(balance),
        interest_rate=Decimal(rate),
        minimum_payment=Decimal(minimum),
    )


def test_avalanche_pays_highest_rate_first() -> None:
    """Avalanche pays the debt with the highest interest rate first."""
    low_rate = _debt("10000", "0.05", "200", nickname="Low Rate")
    high_rate = _debt("10000", "0.20", "200", nickname="High Rate")

    plan = project_payoff([low_rate, high_rate], Decimal("500"), "avalanche")

    assert len(plan.payoff_order) == 2
    assert plan.payoff_order[0] == "High Rate", (
        "Avalanche should pay off the highest-rate debt first"
    )


def test_snowball_pays_lowest_balance_first() -> None:
    """Snowball pays the debt with the lowest balance first."""
    small = _debt("2000", "0.10", "50", nickname="Small Balance")
    large = _debt("20000", "0.10", "400", nickname="Large Balance")

    plan = project_payoff([small, large], Decimal("200"), "snowball")

    assert len(plan.payoff_order) == 2
    assert plan.payoff_order[0] == "Small Balance", (
        "Snowball should pay off the lowest-balance debt first"
    )


def test_avalanche_order_by_rate_at_zero_extra() -> None:
    """Regression: with $0 extra, avalanche still orders by interest rate, not by the
    incidental order debts retire under minimum payments.

    Mirrors the Brooks household: the highest-rate debt (Sapphire, 21%) carries a
    larger balance than a lower-rate debt (Personal Loan, 11%), so under minimums
    alone the smaller debt retires first. Avalanche must still list the highest-rate
    debt first.
    """
    sapphire = _debt("9000", "0.21", "270", nickname="Sapphire Card")
    personal = _debt("4000", "0.11", "130", nickname="Personal Loan")
    student = _debt("40000", "0.06", "420", nickname="Federal Student Loan")

    avalanche = project_payoff([sapphire, personal, student], Decimal("0"), "avalanche")
    snowball = project_payoff([sapphire, personal, student], Decimal("0"), "snowball")

    assert avalanche.payoff_order == [
        "Sapphire Card",
        "Personal Loan",
        "Federal Student Loan",
    ], "Avalanche orders by interest rate descending, even with no extra payment"
    assert snowball.payoff_order == [
        "Personal Loan",
        "Sapphire Card",
        "Federal Student Loan",
    ], "Snowball orders by balance ascending, even with no extra payment"


def test_avalanche_less_interest_than_snowball() -> None:
    """When rates differ, avalanche total interest should be less than snowball."""
    # Two debts with different rates — avalanche saves more on interest
    low_rate = _debt("5000", "0.05", "100", nickname="Low")
    high_rate = _debt("15000", "0.20", "300", nickname="High")

    avalanche = project_payoff([low_rate, high_rate], Decimal("200"), "avalanche")
    snowball = project_payoff([low_rate, high_rate], Decimal("200"), "snowball")

    assert avalanche.total_interest_paid < snowball.total_interest_paid, (
        "Avalanche should pay less total interest than snowball when rates differ"
    )


def test_paid_off_debt_rolls_minimum() -> None:
    """When debt A pays off, its minimum should be added to extra for debt B."""
    # Small debt with low minimum — will pay off quickly
    small = _debt("500", "0.05", "50", nickname="Small")
    # Large debt with higher minimum
    large = _debt("10000", "0.10", "200", nickname="Large")

    # Use avalanche: large has higher rate, so extra goes to large first
    # With snowball, small pays first and its $50 min rolls into extra for large
    plan = project_payoff([small, large], Decimal("0"), "snowball")

    assert plan.payoff_order[0] == "Small"
    # After Small pays off, large should pay off faster due to rolled minimum
    assert plan.months_to_payoff < 200, "Payoff should happen well within 200 months"


def test_single_debt_no_extra() -> None:
    """Single debt, no extra payment: months ≈ ceil(balance / min_payment) approximately."""
    balance = Decimal("1200")
    minimum = Decimal("100")
    # 0% interest simplifies the math: exactly 12 months
    debt = _debt("1200", "0.0", "100")

    plan = project_payoff([debt], Decimal("0"), "avalanche")

    # With 0% interest: exactly balance / minimum months
    expected_months = math.ceil(float(balance / minimum))
    # Allow ±1 due to rounding effects of cent-level Decimal arithmetic
    assert abs(plan.months_to_payoff - expected_months) <= 1, (
        f"Expected ~{expected_months} months, got {plan.months_to_payoff}"
    )


def test_max_months_cap() -> None:
    """Very low minimum with no extra should hit the 600-month cap."""
    # $100,000 at 25% interest with only $50 minimum — will never pay off
    debt = _debt("100000", "0.25", "50")

    plan = project_payoff([debt], Decimal("0"), "avalanche")

    assert plan.months_to_payoff == 600, (
        "Should hit the 600-month cap when minimum is too low to cover interest"
    )
    # Balance should still be positive after 600 months
    assert plan.monthly_series[-1].total_remaining > Decimal(0)
