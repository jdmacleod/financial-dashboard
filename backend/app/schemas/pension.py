import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PensionAccountCreate(BaseModel):
    member_id: uuid.UUID | None = None
    plan_name: str | None = None
    administrator: str | None = None
    monthly_benefit_estimate: Decimal | None = Field(default=None, ge=0)
    eligibility_age: int | None = Field(default=None, ge=50, le=90)
    eligibility_date: date | None = None
    cola_adjustment_rate: Decimal = Field(default=Decimal("0.02"), ge=0, le=Decimal("0.10"))
    is_vested: bool = False
    vesting_date: date | None = None
    survivor_benefit_percent: Decimal | None = Field(default=None, ge=0, le=Decimal("1.0"))
    notes: str | None = None


class PensionAccountUpdate(BaseModel):
    member_id: uuid.UUID | None = None
    plan_name: str | None = None
    administrator: str | None = None
    monthly_benefit_estimate: Decimal | None = Field(default=None, ge=0)
    eligibility_age: int | None = Field(default=None, ge=50, le=90)
    eligibility_date: date | None = None
    cola_adjustment_rate: Decimal | None = Field(default=None, ge=0, le=Decimal("0.10"))
    is_vested: bool | None = None
    vesting_date: date | None = None
    survivor_benefit_percent: Decimal | None = Field(default=None, ge=0, le=Decimal("1.0"))
    notes: str | None = None


class PensionAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    member_id: uuid.UUID | None
    plan_name: str | None
    administrator: str | None
    monthly_benefit_estimate: Decimal | None
    eligibility_age: int | None
    eligibility_date: date | None
    cola_adjustment_rate: Decimal
    is_vested: bool
    vesting_date: date | None
    survivor_benefit_percent: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
