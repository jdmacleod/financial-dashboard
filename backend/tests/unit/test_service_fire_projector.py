"""Pure unit tests for fire_projector.py — no database required."""

from __future__ import annotations

from datetime import date
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
    """With a high savings rate the portfolio reaches FIRE, and the projection keeps
    running past it (run-to-horizon) instead of stopping at the first FIRE year."""
    stream = _salary_stream(amount="120000", start_year=2026)
    scenario = _scenario(
        target_spend="60000",
        portfolio="500000",
        streams=[stream],
    )
    projections = project(scenario, from_year=2026, member_dob=None)

    # No DOB -> can't apply the age horizon, so the full 75-year cap is used.
    assert len(projections) == 75
    fire_years = [p for p in projections if p.is_fire_year]
    assert len(fire_years) >= 1, "FIRE should be reached"
    first_fire = fire_years[0]
    assert first_fire.portfolio >= first_fire.fire_number
    # Once FIRE is reached, a still-saving portfolio stays above the FIRE number.
    after = [p for p in projections if p.year >= first_fire.year]
    assert all(p.is_fire_year for p in after)


def test_age_is_sourced_from_age_service() -> None:
    """Regression: projection age now flows through age.age_in_year. Each row's
    age must equal calendar_year - birth_year for a known DOB, and stay None when
    no DOB is supplied."""
    scenario = _scenario(streams=[_salary_stream()])

    with_dob = project(scenario, from_year=2026, member_dob=date(1980, 7, 15))
    assert with_dob[0].age == 46  # 2026 - 1980
    assert with_dob[1].age == 47  # 2027 - 1980

    without_dob = project(scenario, from_year=2026, member_dob=None)
    assert all(p.age is None for p in without_dob)


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


def test_runs_to_life_expectancy_not_to_absurd_age() -> None:
    """Regression: an already-retired member's projection stops at the life-expectancy
    horizon, not a blind 75 years that ran a 74-year-old out to age 148."""
    # Born 1952 -> age 74 in 2026.
    scenario = _scenario(target_spend="280000", portfolio="7500000", streams=[])
    projections = project(scenario, from_year=2026, member_dob=date(1952, 1, 1), horizon_age=100)

    ages = [p.age for p in projections if p.age is not None]
    assert max(ages) <= 100, "projection must not run past the life-expectancy horizon"
    assert ages[-1] == 100, "projection should reach the horizon age"
    assert len(projections) < 75, "horizon should cap the projection well under the 75-year limit"


def test_decumulation_income_offsets_drawdown_and_portfolio_sustains() -> None:
    """Regression (H5/H6 shape): a retiree with guaranteed post-retirement income and a
    large portfolio sustains the plan. The income offsets the drawdown (it is counted in
    annual_income and the portfolio), so the balance never craters into the negatives."""
    # All streams are post-retirement (is_pre_retirement=False), like the seeded
    # decumulation households. Income ~ spend, on a large portfolio at 5.5% return.
    ss = IncomeStream(
        id=str(uuid4()),
        label="Social Security",
        type=IncomeStreamType.social_security,
        amount_annual=Decimal("65000"),
        growth_rate_annual=Decimal("0.025"),
        start_year=2026,
        end_year=None,
        is_pre_retirement=False,
    )
    pension = IncomeStream(
        id=str(uuid4()),
        label="Pension",
        type=IncomeStreamType.pension,
        amount_annual=Decimal("180000"),
        growth_rate_annual=Decimal("0"),
        start_year=2026,
        end_year=None,
        is_pre_retirement=False,
    )
    scenario = _scenario(
        target_spend="280000",
        swr="0.04",
        ret="0.055",
        inf="0.03",
        portfolio="7500000",
        streams=[ss, pension],
    )
    projections = project(scenario, from_year=2026, member_dob=date(1952, 1, 1), horizon_age=100)

    # Post-retirement income now feeds annual_income (fixes the "$0 income" display)
    # and the portfolio drawdown.
    assert projections[0].annual_income > Decimal(0)
    # The portfolio sustains the whole horizon — never crashes into the negatives.
    assert all(p.portfolio > Decimal(0) for p in projections)
    # And it stays at/above the FIRE number throughout (this household is FIRE).
    assert all(p.is_fire_year for p in projections)


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
