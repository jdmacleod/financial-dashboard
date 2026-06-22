import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.investment_lot import LOT_BASIS_TYPES

_BASIS_TYPE_PATTERN = f"^({'|'.join(LOT_BASIS_TYPES)})$"


class InvestmentLotCreate(BaseModel):
    account_id: uuid.UUID
    ticker: str = Field(..., min_length=1, max_length=16)
    shares: Decimal = Field(..., gt=0)
    basis_per_share: Decimal = Field(..., ge=0)
    acquired_date: date
    basis_type: str = Field(..., pattern=_BASIS_TYPE_PATTERN)


class InvestmentLotUpdate(BaseModel):
    ticker: str | None = Field(default=None, min_length=1, max_length=16)
    shares: Decimal | None = Field(default=None, gt=0)
    basis_per_share: Decimal | None = Field(default=None, ge=0)
    acquired_date: date | None = None
    basis_type: str | None = Field(default=None, pattern=_BASIS_TYPE_PATTERN)


class InvestmentLotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    ticker: str
    shares: Decimal
    basis_per_share: Decimal
    acquired_date: date
    basis_type: str
    created_at: datetime
