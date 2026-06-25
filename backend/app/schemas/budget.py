import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BudgetPeriod = Literal["monthly", "quarterly", "annual"]


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    period: BudgetPeriod = "monthly"
    amount: Decimal = Field(ge=0)
    effective_from: date
    effective_to: date | None = None


class BudgetUpdate(BaseModel):
    period: BudgetPeriod | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    category_id: uuid.UUID
    period: BudgetPeriod
    amount: Decimal
    effective_from: date
    effective_to: date | None
