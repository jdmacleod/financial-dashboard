import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class MemberCreate(BaseModel):
    display_name: str
    role: Literal["primary", "partner", "dependent"] = "partner"
    date_of_birth: date | None = None


class MemberUpdate(BaseModel):
    display_name: str | None = None
    role: Literal["primary", "partner", "dependent"] | None = None
    date_of_birth: date | None = None
    is_active: bool | None = None


class DashboardWidget(BaseModel):
    id: str
    visible: bool = True
    order: int


class DashboardLayoutUpdate(BaseModel):
    widgets: list[DashboardWidget]


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    display_name: str
    role: str
    date_of_birth: date | None
    is_active: bool
    settings: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
