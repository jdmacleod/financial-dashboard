from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class IncomeStreamType(StrEnum):
    salary = "salary"
    rental = "rental"
    consulting = "consulting"
    pension = "pension"
    social_security = "social_security"
    investment = "investment"
    other = "other"


class IncomeStream(BaseModel):
    id: str  # client-generated UUID string
    label: str = Field(max_length=100)
    type: IncomeStreamType
    amount_annual: Decimal = Field(ge=0)
    growth_rate_annual: Decimal = Field(ge=Decimal("-1.0"), le=Decimal("1.0"))
    start_year: int = Field(ge=1900, le=2200)
    end_year: int | None = None
    is_pre_retirement: bool = True
    notes: str | None = None
    real_estate_property_id: str | None = None
    auto_detected: bool = False
    detected_at: datetime | None = None


class FireScenarioCreate(BaseModel):
    name: str = Field(max_length=100)
    target_annual_spend: Decimal = Field(ge=0)
    safe_withdrawal_rate: Decimal = Field(
        default=Decimal("0.04"), ge=Decimal("0.01"), le=Decimal("0.20")
    )
    expected_annual_return: Decimal = Field(
        default=Decimal("0.07"), ge=Decimal("0.0"), le=Decimal("1.0")
    )
    expected_inflation_rate: Decimal = Field(
        default=Decimal("0.03"), ge=Decimal("0.0"), le=Decimal("0.20")
    )
    target_retirement_age: int | None = Field(default=None, ge=18, le=100)
    additional_income_streams: list[IncomeStream] = Field(default_factory=list)


class FireScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    target_annual_spend: Decimal | None = Field(default=None, ge=0)
    safe_withdrawal_rate: Decimal | None = None
    expected_annual_return: Decimal | None = None
    expected_inflation_rate: Decimal | None = None
    target_retirement_age: int | None = None
    additional_income_streams: list[IncomeStream] | None = None
    detection_trailing_months: int | None = Field(default=None, ge=1, le=60)


class FireScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    name: str
    target_annual_spend: Decimal
    safe_withdrawal_rate: Decimal
    expected_annual_return: Decimal
    expected_inflation_rate: Decimal
    target_retirement_age: int | None
    additional_income_streams: list[IncomeStream]
    detected_annual_income: Decimal | None
    detected_annual_expenses: Decimal | None
    detected_savings_rate: Decimal | None
    detected_portfolio_value: Decimal | None
    detection_trailing_months: int
    detected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FireDetectionResponse(BaseModel):
    scenario: FireScenarioResponse
    warnings: list[str]


class YearProjectionResponse(BaseModel):
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


class FireProjectionSummary(BaseModel):
    fire_year: int | None
    fire_age: int | None
    years_to_fire: int | None
    fire_number: Decimal
    headline: str


class FireProjectionResponse(BaseModel):
    summary: FireProjectionSummary
    projections: list[YearProjectionResponse]


class DebtWithAccountResponse(BaseModel):
    debt_id: uuid.UUID
    account_id: uuid.UUID
    nickname: str
    current_balance: Decimal
    interest_rate: Decimal
    minimum_payment: Decimal


class DebtPayoffMonthResponse(BaseModel):
    month: int
    date: date
    total_remaining: Decimal
    per_debt: dict[str, Decimal]  # str(UUID) → balance


class DebtPayoffPlanResponse(BaseModel):
    strategy: str
    months_to_payoff: int
    total_interest_paid: Decimal
    payoff_date: date
    monthly_series: list[DebtPayoffMonthResponse]
    payoff_order: list[str]


class DebtPayoffComparisonResponse(BaseModel):
    debts: list[DebtWithAccountResponse]
    avalanche: DebtPayoffPlanResponse
    snowball: DebtPayoffPlanResponse
