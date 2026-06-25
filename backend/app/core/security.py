import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt hashes at most the first 72 bytes of the secret and, since 5.0, raises
# on anything longer instead of silently truncating. We truncate explicitly to
# preserve the prior behavior (passlib did the same), so passwords keep hashing
# and verifying identically. Hashes use the standard $2b$ format, so credentials
# created under the previous passlib backend verify unchanged.
_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def generate_temporary_password() -> str:
    """A strong, URL-safe temporary password for provisioned users (~22 chars).

    Server-generated so the inviter never invents a credential; the user is
    forced to replace it on first login (must_change_password).
    """
    return secrets.token_urlsafe(16)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except ValueError:
        # Malformed/unknown hash string — treat as a non-match rather than raising.
        return False


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
