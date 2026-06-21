from pydantic import BaseModel


class LoginRequest(BaseModel):
    # str not EmailStr: login is a DB lookup; EmailStr rejects .local domains used in demo data
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme name, not a credential


class ReauthRequest(BaseModel):
    password: str


class ReauthResponse(BaseModel):
    reauth_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
