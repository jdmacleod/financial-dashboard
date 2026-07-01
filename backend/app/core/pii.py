"""Server-side PII redaction for ingested transaction text.

The ingest CLI classifies PII locally as a UX hint, but the SERVER is the trust
boundary (eng review, outside-voice #1): we never store a plaintext account /
routing / card number in the plaintext payee or memo columns, regardless of what
the client labelled. A statement line like "ACH PAYMENT ACCT 4111111111111111"
must not land verbatim.

This is deterministic (regex + Luhn), never an LLM judgment. It over-redacts on
purpose — masking a stray confirmation number is acceptable; leaking an account
number is not. Long digit runs are masked to their last 4 (the industry-standard
non-PII form, e.g. ``****1234``), which still lets a human recognize the line.
"""

import re

# 8+ digits, optionally split by spaces or hyphens (covers account, routing,
# and 13-19 digit card numbers as they appear on statements).
_DIGIT_RUN = re.compile(r"\b\d[\d -]{6,}\d\b")
_MIN_SENSITIVE_DIGITS = 8


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _mask(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group())
    if len(digits) < _MIN_SENSITIVE_DIGITS:
        return match.group()
    return "*" * (len(digits) - 4) + digits[-4:]


def redact_pii(text: str | None) -> str | None:
    """Mask account/routing/card-like digit runs to their last 4. Idempotent."""
    if not text:
        return text
    return _DIGIT_RUN.sub(_mask, text)


def contains_pii(text: str | None) -> bool:
    """True if the text still carries an unmasked sensitive digit run.

    Distinguishes a real account/card number (Luhn-valid, or routing/account
    length) from a short reference. Used to assert the redaction invariant in
    tests and as a server-side guard.
    """
    if not text:
        return False
    for match in _DIGIT_RUN.finditer(text):
        digits = re.sub(r"\D", "", match.group())
        if len(digits) >= _MIN_SENSITIVE_DIGITS:
            return True
        if len(digits) >= 13 and _luhn_ok(digits):
            return True
    return False
