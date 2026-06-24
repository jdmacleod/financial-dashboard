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


def project(
    scenario: FireScenario,
    from_year: int,
    member_dob: date | None,
) -> list[YearProjection]:
    """Year-by-year compound projection, capped at 75 years."""
    portfolio = scenario.detected_portfolio_value or Decimal(0)
    fire_number = scenario.target_annual_spend / scenario.safe_withdrawal_rate
    projections: list[YearProjection] = []

    for year in range(from_year, from_year + 75):
        age = age_in_year(member_dob, year)

        # Pre-retirement income streams active this year
        annual_income = sum(
            (
                _stream_amount(s, year)
                for s in scenario.income_streams
                if s.is_pre_retirement and _stream_active(s, year)
            ),
            Decimal(0),
        )

        # Inflation-adjusted spend target
        annual_spend = scenario.target_annual_spend * (
            (1 + scenario.expected_inflation_rate) ** (year - from_year)
        )

        annual_savings = annual_income - annual_spend

        # Grow portfolio and add savings
        portfolio = portfolio * (1 + scenario.expected_annual_return) + annual_savings

        # Post-retirement supplemental income streams (reduce withdrawal need)
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

        if is_fire_year:
            break

    return projections
