import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

ValuationSource = Literal["manual", "api_attom", "api_estated"]
PropertyTypeLiteral = Literal[
    "primary_residence", "rental", "vacation", "commercial", "land", "other"
]


class PropertyCreate(BaseModel):
    account_id: uuid.UUID
    address: str
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    linked_mortgage_account_id: uuid.UUID | None = None
    property_type: PropertyTypeLiteral = "primary_residence"


class PropertyUpdate(BaseModel):
    address: str | None = None
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    linked_mortgage_account_id: uuid.UUID | None = None
    property_type: PropertyTypeLiteral | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    nickname: str
    address: str
    purchase_date: date | None
    purchase_price: Decimal | None
    linked_mortgage_account_id: uuid.UUID | None
    property_type: str
    current_estimated_value: Decimal | None
    current_value_as_of: date | None
    gain_loss: Decimal | None = None
    gain_loss_pct: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def compute_gain_loss(self) -> Self:
        if self.purchase_price is not None and self.current_estimated_value is not None:
            self.gain_loss = self.current_estimated_value - self.purchase_price
            if self.purchase_price != 0:
                self.gain_loss_pct = (
                    (self.current_estimated_value - self.purchase_price)
                    / self.purchase_price
                    * Decimal("100")
                )
        return self


class PropertyEquityResponse(BaseModel):
    property_value: Decimal
    valuation_date: date
    valuation_source: str
    mortgage_balance: Decimal | None
    mortgage_balance_as_of: date | None
    mortgage_balance_visible: bool
    equity: Decimal | None


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
