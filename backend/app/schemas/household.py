import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    settings: dict[str, Any]
    created_at: datetime


class HouseholdUpdate(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None
