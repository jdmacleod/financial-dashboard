"""Pure unit tests for fire_projector.py — no database required."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.schemas.fire import IncomeStream, IncomeStreamType
from app.services.fire_projector import FireScenario, project


def _scenario(
    target_spend: str = "60000",
    swr: str = "0.04",
    ret: str = "0.07",
    inf: str = "0.03",
    portfolio: str | None = "500000",
    streams: list[IncomeStream] | None = None,
) -> FireScenario:
    return FireScenario(
        id=uuid4(),
        target_annual_spend=Decimal(target_spend),
        safe_withdrawal_rate=Decimal(swr),
        expected_annual_return=Decimal(ret),
        expected_inflation_rate=Decimal(inf),
        income_streams=streams or [],
        detected_portfolio_value=Decimal(portfolio) if portfolio else None,
    )


def _salary_stream(
    amount: str = "120000",
    start_year: int = 2026,
    end_year: int | None = None,
    growth: str = "0.03",
    is_pre_retirement: bool = True,
) -> IncomeStream:
    return IncomeStream(
        id=str(uuid4()),
        label="Salary",
        type=IncomeStreamType.salary,
        amount_annual=Decimal(amount),
        growth_rate_annual=Decimal(growth),
        start_year=start_year,
        end_year=end_year,
        is_pre_retirement=is_pre_retirement,
    )


def test_basic_projection() -> None:
    """With a high savings rate and pre-retirement salary, FIRE year should be found."""
    stream = _salary_stream(amount="120000", start_year=2026)
    scenario = _scenario(
        target_spend="60000",
        portfolio="500000",
        streams=[stream],
    )
    projections = project(scenario, from_year=2026, member_dob=None)

    assert len(projections) > 0
    fire_years = [p for p in projections if p.is_fire_year]
    assert len(fire_years) == 1, "Exactly one FIRE year should be found"
    assert fire_years[0].portfolio >= fire_years[0].fire_number


def test_stream_end_year_respected() -> None:
    """A consulting stream ending in 2030 should not contribute income after that year."""
    consulting = IncomeStream(
        id=str(uuid4()),
        label="Consulting",
        type=IncomeStreamType.consulting,
        amount_annual=Decimal("50000"),
        growth_rate_annual=Decimal("0"),
        start_year=2026,
        end_year=2030,
        is_pre_retirement=True,
    )
    scenario = _scenario(
        target_spend="80000",
        portfolio="200000",
        streams=[consulting],
    )
    projections = project(scenario, from_year=2026, member_dob=None)

    # After 2030, annual_income should be 0 (consulting stream inactive)
    post_2030 = [p for p in projections if p.year > 2030]
    for proj in post_2030:
        assert proj.annual_income == Decimal(0), (
            f"Year {proj.year} should have zero income after stream end_year"
        )


def test_post_retirement_social_security() -> None:
    """SS stream (is_pre_retirement=False) reduces effective_withdrawal after FIRE."""
    ss = IncomeStream(
        id=str(uuid4()),
        label="Social Security",
        type=IncomeStreamType.social_security,
        amount_annual=Decimal("20000"),
        growth_rate_annual=Decimal("0"),
        start_year=2026,
        end_year=None,
        is_pre_retirement=False,
    )
    salary = _salary_stream(amount="150000", start_year=2026)
    scenario = _scenario(
        target_spend="60000",
        portfolio="1000000",
        streams=[salary, ss],
    )
    projections = project(scenario, from_year=2026, member_dob=None)

    # At least some projections should show supplemental income from SS
    ss_projections = [p for p in projections if p.supplemental_income > Decimal(0)]
    assert len(ss_projections) > 0

    # effective_withdrawal should be reduced by SS amount
    for proj in ss_projections:
        expected_withdrawal = max(proj.annual_spend - proj.supplemental_income, Decimal(0))
        assert proj.effective_withdrawal == expected_withdrawal


def test_no_fire_within_75_years() -> None:
    """With very low savings, FIRE shouldn't be reached. Should return max 75 projections."""
    # Spend > income → negative savings, portfolio shrinks
    scenario = _scenario(
        target_spend="200000",
        portfolio="100000",
        streams=[],  # no income
    )
    projections = project(scenario, from_year=2026, member_dob=None)

    assert len(projections) == 75
    assert not any(p.is_fire_year for p in projections)


def test_decimal_arithmetic_no_float() -> None:
    """All numeric fields in projections must be Decimal, not float."""
    stream = _salary_stream(amount="120000")
    scenario = _scenario(portfolio="500000", streams=[stream])
    projections = project(scenario, from_year=2026, member_dob=None)

    assert len(projections) > 0
    for proj in projections:
        assert isinstance(proj.portfolio, Decimal), "portfolio must be Decimal"
        assert isinstance(proj.annual_income, Decimal), "annual_income must be Decimal"
        assert isinstance(proj.annual_spend, Decimal), "annual_spend must be Decimal"
        assert isinstance(proj.annual_savings, Decimal), "annual_savings must be Decimal"
        assert isinstance(proj.supplemental_income, Decimal), "supplemental_income must be Decimal"
        assert isinstance(proj.effective_withdrawal, Decimal), (
            "effective_withdrawal must be Decimal"
        )
        assert isinstance(proj.fire_number, Decimal), "fire_number must be Decimal"
