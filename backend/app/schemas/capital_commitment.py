import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CapitalCommitmentCreate(BaseModel):
    fund_name: str = Field(..., min_length=1, max_length=200)
    committed_amount: Decimal = Field(..., gt=0)
    called_to_date: Decimal = Field(default=Decimal("0"), ge=0)
    nav_account_id: uuid.UUID
    vintage_year: int = Field(..., ge=1900, le=2200)


class CapitalCommitmentUpdate(BaseModel):
    fund_name: str | None = Field(default=None, min_length=1, max_length=200)
    committed_amount: Decimal | None = Field(default=None, gt=0)
    called_to_date: Decimal | None = Field(default=None, ge=0)
    nav_account_id: uuid.UUID | None = None
    vintage_year: int | None = Field(default=None, ge=1900, le=2200)


class CapitalCommitmentResponse(BaseModel):
    # fund_name is decrypted in the service layer (stored as fund_name_enc BYTEA).
    id: uuid.UUID
    household_id: uuid.UUID
    fund_name: str
    committed_amount: Decimal
    called_to_date: Decimal
    nav_account_id: uuid.UUID
    vintage_year: int
    created_at: datetime
