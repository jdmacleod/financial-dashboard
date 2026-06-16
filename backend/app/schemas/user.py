import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    member_id: uuid.UUID
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: uuid.UUID | None
    email: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime
