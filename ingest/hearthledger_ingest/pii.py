"""Local PII redaction — a UX HINT only.

The HearthLedger server re-runs redaction at the staging boundary and is the
authoritative guard (it never trusts the client's split). We redact here so the
operator sees masked numbers in the CLI preview and nothing sensitive sits in
local logs, but a miss here is harmless: the server catches it.

Kept deliberately in sync with the server's core/pii.py.
"""

import re

_DIGIT_RUN = re.compile(r"\b\d[\d -]{6,}\d\b")
_MIN_SENSITIVE_DIGITS = 8


def _mask(match: "re.Match[str]") -> str:
    digits = re.sub(r"\D", "", match.group())
    if len(digits) < _MIN_SENSITIVE_DIGITS:
        return match.group()
    return "*" * (len(digits) - 4) + digits[-4:]


def redact_pii(text: str | None) -> str | None:
    """Mask account/card/routing-like digit runs to their last 4. Idempotent."""
    if not text:
        return text
    return _DIGIT_RUN.sub(_mask, text)
