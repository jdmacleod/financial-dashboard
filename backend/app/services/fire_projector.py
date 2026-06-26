from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.schemas.fire import IncomeStream
from app.services.age import age_in_year


@dataclass
class YearProjection:
    year: int
    age: int | None
    portfolio: Decimal
    annual_income: Decimal
    annual_spend: Decimal
    annual_savings: Decimal
    supplemental_income: Decimal
    effective_withdrawal: Decimal
    fire_number: Decimal
    is_fire_year: bool


@dataclass
class FireScenario:
    """Mirrors the fire_scenarios row. All rate and dollar fields are Decimal."""

    id: UUID
    target_annual_spend: Decimal
    safe_withdrawal_rate: Decimal
    expected_annual_return: Decimal
    expected_inflation_rate: Decimal
    income_streams: list[IncomeStream]
    detected_portfolio_value: Decimal | None


def _stream_amount(stream: IncomeStream, year: int) -> Decimal:
    """Compute income stream amount for the given year with compound growth."""
    years_elapsed = year - stream.start_year
    if years_elapsed < 0:
        return Decimal(0)
    # Decimal ** int is exact; growth_rate_annual is already Decimal from DB
    return stream.amount_annual * (1 + stream.growth_rate_annual) ** years_elapsed


def _stream_active(stream: IncomeStream, year: int) -> bool:
    """Check whether a stream contributes income in the given year."""
    return stream.start_year <= year and (stream.end_year is None or stream.end_year >= year)


# The projection runs to a life-expectancy horizon so a decumulation scenario
# shows the whole retirement arc, not just the moment FIRE is reached. When the
# member's date of birth is unknown we can't compute age, so we fall back to the
# MAX_PROJECTION_YEARS cap.
DEFAULT_HORIZON_AGE = 100
MAX_PROJECTION_YEARS = 75


def project(
    scenario: FireScenario,
    from_year: int,
    member_dob: date | None,
    horizon_age: int = DEFAULT_HORIZON_AGE,
) -> list[YearProjection]:
    """Year-by-year compound projection from the current portfolio to life expectancy.

    Unified accumulation + decumulation. Every income stream active in a given year
    (salary while working, then Social Security / pensions / annuity income in
    retirement) is netted against the inflation-adjusted spend; the remainder is
    added to or drawn from the portfolio. Each stream's start_year/end_year already
    bounds when it is active (salary ends at retirement, SS begins at the claiming
    age), so they are netted uniformly regardless of the is_pre_retirement flag.

    The loop runs to ``horizon_age`` rather than breaking at the first FIRE year, so
    a household already past its FIRE number still shows whether the portfolio
    sustains the full retirement. ``is_fire_year`` is flagged on every qualifying
    year; the caller takes the first one for the headline.
    """
    portfolio = scenario.detected_portfolio_value or Decimal(0)
    fire_number = scenario.target_annual_spend / scenario.safe_withdrawal_rate
    projections: list[YearProjection] = []

    for offset in range(MAX_PROJECTION_YEARS):
        year = from_year + offset
        age = age_in_year(member_dob, year)

        # All income streams active this year contribute to cash flow.
        annual_income = sum(
            (_stream_amount(s, year) for s in scenario.income_streams if _stream_active(s, year)),
            Decimal(0),
        )

        # Inflation-adjusted spend target
        annual_spend = scenario.target_annual_spend * (
            (1 + scenario.expected_inflation_rate) ** offset
        )

        annual_savings = annual_income - annual_spend

        # Grow the portfolio, then apply the net cash flow (positive = saving,
        # negative = drawing down).
        portfolio = portfolio * (1 + scenario.expected_annual_return) + annual_savings

        # Guaranteed post-retirement income (SS / pension / annuity), surfaced so the
        # UI can show the portfolio's effective withdrawal need separately from total
        # income. Display split only — already counted in annual_income above.
        supplemental = sum(
            (
                _stream_amount(s, year)
                for s in scenario.income_streams
                if not s.is_pre_retirement and _stream_active(s, year)
            ),
            Decimal(0),
        )

        effective_withdrawal = max(annual_spend - supplemental, Decimal(0))
        is_fire_year = portfolio >= fire_number

        projections.append(
            YearProjection(
                year=year,
                age=age,
                portfolio=portfolio,
                annual_income=annual_income,
                annual_spend=annual_spend,
                annual_savings=annual_savings,
                supplemental_income=supplemental,
                effective_withdrawal=effective_withdrawal,
                fire_number=fire_number,
                is_fire_year=is_fire_year,
            )
        )

        # Stop at life expectancy once we can place the member in time.
        if age is not None and age >= horizon_age:
            break

    return projections
