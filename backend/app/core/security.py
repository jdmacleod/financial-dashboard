import hashlib
import hmac
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


# --- Personal access tokens (programmatic API auth) ---------------------------
#
# PATs are NOT bcrypt-hashed. bcrypt is a deliberately-slow password primitive
# (and truncates at 72 bytes); a PAT is high-entropy random and verified on
# every API request, so a fast SHA-256 of the secret is the correct choice.
# Wire format:  hl_pat_<prefix>.<secret>
#   - prefix  : non-secret, indexed, O(1) lookup of the token row
#   - secret  : token_urlsafe(32); only its SHA-256 is stored
# The full token is shown to the user exactly once, at creation.

PAT_PREFIX = "hl_pat_"


def _hash_pat_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_pat() -> tuple[str, str, str]:
    """Mint a PAT. Returns (full_token, lookup_prefix, token_hash).

    Only ``token_hash`` is persisted; ``full_token`` is returned to the caller
    once and never stored.
    """
    prefix = secrets.token_urlsafe(9)[:12]
    secret = secrets.token_urlsafe(32)
    full = f"{PAT_PREFIX}{prefix}.{secret}"
    return full, prefix, _hash_pat_secret(secret)


def parse_pat(token: str) -> tuple[str, str] | None:
    """Split a presented bearer credential into (prefix, secret).

    Returns None when the credential is not PAT-shaped (e.g. it is a JWT), so
    the auth layer can route deterministically by prefix instead of guessing.
    """
    if not token.startswith(PAT_PREFIX):
        return None
    prefix, sep, secret = token[len(PAT_PREFIX) :].partition(".")
    if not sep or not prefix or not secret:
        return None
    return prefix, secret


def verify_pat_secret(secret: str, token_hash: str) -> bool:
    return hmac.compare_digest(_hash_pat_secret(secret), token_hash)
