import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


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
