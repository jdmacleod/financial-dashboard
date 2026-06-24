from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.member import BirthDate, MemberResponse
from app.schemas.user import UserResponse


class ProvisionRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=80)
    role: Literal["primary", "partner", "dependent"] = "partner"
    # str not EmailStr: matches LoginRequest — login is a DB lookup and demo data
    # uses .local domains that EmailStr rejects.
    email: str = Field(..., min_length=3, max_length=255)
    date_of_birth: BirthDate = None


class ProvisionResponse(BaseModel):
    member: MemberResponse
    user: UserResponse
    # Plaintext temporary password — returned ONCE, never persisted in plaintext
    # and never written to the audit log. The inviter conveys it to the new person.
    temporary_password: str


class TemporaryPasswordResponse(BaseModel):
    temporary_password: str
