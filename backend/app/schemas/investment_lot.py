import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
