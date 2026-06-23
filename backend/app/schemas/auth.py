from pydantic import BaseModel


class LoginRequest(BaseModel):
    # str not EmailStr: login is a DB lookup; EmailStr rejects .local domains used in demo data
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme name, not a credential
    # True when the user signed in with a provisioned temporary password and must
    # set their own before continuing. The frontend routes to the forced reset.
    must_change_password: bool = False


class ReauthRequest(BaseModel):
    password: str


class ReauthResponse(BaseModel):
    reauth_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
