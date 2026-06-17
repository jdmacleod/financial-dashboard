import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    parent_category_id: uuid.UUID | None = None
    color_hex: str = "#888888"
    icon: str | None = None
    is_income: bool = False


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_category_id: uuid.UUID | None = None
    color_hex: str | None = None
    icon: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    name: str
    parent_category_id: uuid.UUID | None
    color_hex: str
    icon: str | None
    is_income: bool
    is_system: bool
    created_at: datetime
