import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    settings: dict
    created_at: datetime


class HouseholdUpdate(BaseModel):
    name: str | None = None
    settings: dict | None = None
