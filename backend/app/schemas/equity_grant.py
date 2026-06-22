import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.equity_grant import EQUITY_GRANT_TYPES

_GRANT_TYPE_PATTERN = f"^({'|'.join(EQUITY_GRANT_TYPES)})$"


class EquityGrantCreate(BaseModel):
    member_id: uuid.UUID
    grant_type: str = Field(..., pattern=_GRANT_TYPE_PATTERN)
    grant_date: date
    shares_granted: Decimal = Field(..., gt=0)
    strike_price: Decimal | None = Field(default=None, ge=0)
    ticker: str = Field(..., min_length=1, max_length=16)
    vesting_schedule: dict[str, Any] = Field(default_factory=dict)
    espp_discount_pct: Decimal | None = Field(default=None, ge=0, le=1)
    espp_lookback: bool | None = None


class EquityGrantUpdate(BaseModel):
    grant_type: str | None = Field(default=None, pattern=_GRANT_TYPE_PATTERN)
    grant_date: date | None = None
    shares_granted: Decimal | None = Field(default=None, gt=0)
    strike_price: Decimal | None = Field(default=None, ge=0)
    ticker: str | None = Field(default=None, min_length=1, max_length=16)
    vesting_schedule: dict[str, Any] | None = None
    espp_discount_pct: Decimal | None = Field(default=None, ge=0, le=1)
    espp_lookback: bool | None = None


class VestingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equity_grant_id: uuid.UUID
    event_date: date
    shares_vested: Decimal
    fmv_at_event: Decimal
    taxable_ordinary_income: Decimal
    amt_preference_amount: Decimal | None
    shares_sold_to_cover: Decimal
    resulting_lot_id: uuid.UUID | None
    created_at: datetime


class EquityGrantResponse(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    member_id: uuid.UUID
    grant_type: str
    grant_date: date
    shares_granted: Decimal
    strike_price: Decimal | None
    ticker: str
    vesting_schedule: dict[str, Any]
    espp_discount_pct: Decimal | None
    espp_lookback: bool | None
    created_at: datetime
    vesting_events: list[VestingEventResponse]
