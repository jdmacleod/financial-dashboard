from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, member_id: str | None, role: str) -> str:
    payload = {
        "sub": user_id,
        "member_id": member_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def create_reauth_token(user_id: str) -> str:
    """Short-lived token (10 min) gating executor-level exports."""
    payload = {
        "sub": user_id,
        "type": "reauth",
        "exp": datetime.now(UTC) + timedelta(minutes=10),
    }
    return str(jwt.encode(payload, settings.secret_key, algorithm="HS256"))


def decode_token(
    token: str, expected_type: Literal["access", "refresh", "reauth"]
) -> dict[str, Any]:
    payload: dict[str, Any] = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise JWTError("Wrong token type")
    return payload
