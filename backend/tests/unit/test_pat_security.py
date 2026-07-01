"""Unit tests for personal-access-token crypto helpers (no DB)."""

from app.core.security import (
    PAT_PREFIX,
    _hash_pat_secret,
    generate_pat,
    parse_pat,
    verify_pat_secret,
)


def test_generate_pat_shape() -> None:
    full, prefix, token_hash = generate_pat()
    assert full.startswith(PAT_PREFIX)
    assert full == f"{PAT_PREFIX}{prefix}.{full.split('.', 1)[1]}"
    assert len(prefix) <= 16
    # SHA-256 hex digest is 64 chars; the secret itself is never returned.
    assert len(token_hash) == 64
    assert prefix not in token_hash


def test_generate_pat_is_unique() -> None:
    a = generate_pat()
    b = generate_pat()
    assert a[0] != b[0]
    assert a[1] != b[1]
    assert a[2] != b[2]


def test_parse_pat_round_trip() -> None:
    full, prefix, _ = generate_pat()
    parsed = parse_pat(full)
    assert parsed is not None
    parsed_prefix, parsed_secret = parsed
    assert parsed_prefix == prefix
    assert full == f"{PAT_PREFIX}{parsed_prefix}.{parsed_secret}"


def test_parse_pat_rejects_non_pat() -> None:
    # A JWT-shaped credential must not be mistaken for a PAT.
    assert parse_pat("eyJhbGciOiJIUzI1NiJ9.body.sig") is None
    assert parse_pat("random-bearer-token") is None


def test_parse_pat_rejects_malformed() -> None:
    assert parse_pat(PAT_PREFIX) is None  # no body
    assert parse_pat(f"{PAT_PREFIX}prefixonly") is None  # no separator
    assert parse_pat(f"{PAT_PREFIX}.secretonly") is None  # empty prefix
    assert parse_pat(f"{PAT_PREFIX}prefix.") is None  # empty secret


def test_verify_pat_secret_matches() -> None:
    full, _, token_hash = generate_pat()
    _, secret = parse_pat(full)  # type: ignore[misc]
    assert verify_pat_secret(secret, token_hash) is True


def test_verify_pat_secret_rejects_wrong_secret() -> None:
    _, _, token_hash = generate_pat()
    assert verify_pat_secret("not-the-secret", token_hash) is False


def test_hash_is_deterministic() -> None:
    assert _hash_pat_secret("abc") == _hash_pat_secret("abc")
    assert _hash_pat_secret("abc") != _hash_pat_secret("abd")
