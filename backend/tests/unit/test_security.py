import time
import uuid

import pytest
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_reauth_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_roundtrip() -> None:
    hashed = hash_password("CorrectHorse123!")
    assert verify_password("CorrectHorse123!", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("CorrectHorse123!")
    assert verify_password("WrongPassword", hashed) is False


def test_hash_password_accepts_over_72_bytes() -> None:
    # bcrypt 5.0 raises on >72 bytes unless truncated; we truncate, so this
    # must not raise and must round-trip on the first 72 bytes.
    long_pw = "a" * 100
    hashed = hash_password(long_pw)
    assert verify_password(long_pw, hashed) is True
    # The 73rd byte onward is ignored (bcrypt's documented limit), so a value
    # sharing the first 72 bytes verifies too.
    assert verify_password("a" * 72, hashed) is True


def test_verify_password_returns_false_on_malformed_hash() -> None:
    assert verify_password("whatever", "not-a-bcrypt-hash") is False


def test_verify_password_accepts_legacy_2b_hash() -> None:
    # A $2b$ hash (the format the previous passlib backend produced) must still
    # verify, so existing stored credentials keep working after the migration.
    import bcrypt

    legacy = bcrypt.hashpw(b"CorrectHorse123!", bcrypt.gensalt(prefix=b"2b")).decode()
    assert legacy.startswith("$2b$")
    assert verify_password("CorrectHorse123!", legacy) is True


def test_access_token_payload_fields() -> None:
    user_id = str(uuid.uuid4())
    member_id = str(uuid.uuid4())
    token = create_access_token(user_id, member_id, "partner")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["member_id"] == member_id
    assert payload["role"] == "partner"
    assert payload["type"] == "access"


def test_access_token_allows_null_member_id() -> None:
    token = create_access_token(str(uuid.uuid4()), None, "primary")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["member_id"] is None


def test_refresh_token_payload_fields() -> None:
    user_id = str(uuid.uuid4())
    token = create_refresh_token(user_id)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"
    assert "role" not in payload


def test_reauth_token_payload_fields() -> None:
    user_id = str(uuid.uuid4())
    token = create_reauth_token(user_id)
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    assert payload["sub"] == user_id
    assert payload["type"] == "reauth"


def test_access_token_expiry_delta() -> None:
    token = create_access_token(str(uuid.uuid4()), None, "primary")
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    now = time.time()
    delta_minutes = (payload["exp"] - now) / 60
    assert (
        settings.access_token_expire_minutes - 1
        <= delta_minutes
        <= settings.access_token_expire_minutes
    )


def test_refresh_token_expiry_delta() -> None:
    token = create_refresh_token(str(uuid.uuid4()))
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    now = time.time()
    delta_days = (payload["exp"] - now) / 86400
    assert (
        settings.refresh_token_expire_days - 1 <= delta_days <= settings.refresh_token_expire_days
    )


def test_reauth_token_expiry_is_ten_minutes() -> None:
    token = create_reauth_token(str(uuid.uuid4()))
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    now = time.time()
    delta_minutes = (payload["exp"] - now) / 60
    assert 9 <= delta_minutes <= 10


def test_decode_token_happy_path() -> None:
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, None, "primary")
    payload = decode_token(token, "access")
    assert payload["sub"] == user_id


def test_decode_token_rejects_wrong_type() -> None:
    token = create_refresh_token(str(uuid.uuid4()))
    with pytest.raises(JWTError):
        decode_token(token, "access")


def test_decode_token_rejects_expired_token() -> None:
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "type": "access", "exp": time.time() - 60},
        settings.secret_key,
        algorithm="HS256",
    )
    with pytest.raises(JWTError):
        decode_token(expired, "access")


def test_decode_token_rejects_tampered_signature() -> None:
    token = create_access_token(str(uuid.uuid4()), None, "primary")
    # Tamper the signature segment (third part), not the last char of the token.
    # The last base64url char may encode only padding bits, so changing it can
    # leave the actual HMAC bytes intact and verification would pass. Modifying
    # a character in the middle of the signature segment reliably corrupts it.
    header, payload, sig = token.split(".")
    mid = len(sig) // 2
    corrupted_sig = sig[:mid] + ("a" if sig[mid] != "a" else "b") + sig[mid + 1 :]
    tampered = f"{header}.{payload}.{corrupted_sig}"
    with pytest.raises(JWTError):
        decode_token(tampered, "access")
