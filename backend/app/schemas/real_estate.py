import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

ValuationSource = Literal["manual", "api_attom", "api_estated"]


class PropertyCreate(BaseModel):
    account_id: uuid.UUID
    address: str
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    linked_mortgage_account_id: uuid.UUID | None = None


class PropertyUpdate(BaseModel):
    address: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    linked_mortgage_account_id: uuid.UUID | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    nickname: str
    address: str
    purchase_date: date | None
    purchase_price: Decimal | None
    linked_mortgage_account_id: uuid.UUID | None
    current_estimated_value: Decimal | None
    current_value_as_of: date | None
    created_at: datetime
    updated_at: datetime


class ValuationCreate(BaseModel):
    valuation_date: date
    estimated_value: Decimal
    source: ValuationSource = "manual"


class ValuationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    real_estate_property_id: uuid.UUID
    valuation_date: date
    estimated_value: Decimal
    source: str
    confidence_score: Decimal | None
    created_at: datetime
