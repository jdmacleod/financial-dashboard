"""Unit tests for server-side PII redaction (core/pii.py)."""

from app.core.pii import contains_pii, redact_pii


def test_redacts_card_number_to_last4() -> None:
    out = redact_pii("ACH PAYMENT 4111111111111111 THANK YOU")
    assert out is not None
    assert "4111111111111111" not in out
    assert out.endswith("THANK YOU")
    assert "1111" in out  # last-4 preserved for human recognition


def test_redacts_account_number_with_separators() -> None:
    out = redact_pii("XFER ACCT 1234-5678-9012 OK")
    assert out is not None
    assert "1234-5678-9012" not in out
    assert "9012" in out


def test_leaves_short_numbers_alone() -> None:
    # Check number / small references are not account-length; keep them.
    assert redact_pii("CHECK 1234") == "CHECK 1234"
    assert redact_pii("STORE #42 PURCHASE") == "STORE #42 PURCHASE"


def test_none_and_empty_passthrough() -> None:
    assert redact_pii(None) is None
    assert redact_pii("") == ""


def test_redaction_is_idempotent() -> None:
    once = redact_pii("ACCT 4111111111111111")
    twice = redact_pii(once)
    assert once == twice


def test_contains_pii_detection() -> None:
    assert contains_pii("ACCT 4111111111111111") is True
    assert contains_pii("****1111") is False  # already masked
    assert contains_pii("CHECK 1234") is False
    assert contains_pii(None) is False


def test_redacted_text_has_no_pii() -> None:
    # The core invariant: nothing redact_pii returns still trips the detector.
    samples = [
        "ACH 4111111111111111",
        "ROUTING 021000021 ACCT 000123456789",
        "POS 5555 5555 5555 4444 STORE",
    ]
    for s in samples:
        assert contains_pii(redact_pii(s)) is False
