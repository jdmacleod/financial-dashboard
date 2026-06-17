import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

BudgetPeriod = Literal["monthly", "annual"]


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    period: BudgetPeriod = "monthly"
    amount: Decimal
    effective_from: date
    effective_to: date | None = None


class BudgetUpdate(BaseModel):
    amount: Decimal | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    category_id: uuid.UUID
    period: str
    amount: Decimal
    effective_from: date
    effective_to: date | None
