from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ReauthRequest(BaseModel):
    password: str


class ReauthResponse(BaseModel):
    reauth_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
