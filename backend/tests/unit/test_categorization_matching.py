"""Unit tests for rule matching semantics (pure, no DB)."""

import uuid
from datetime import UTC, datetime

from app.db.models.category_rule import CategoryRule
from app.services.categorization import _normalize, _rule_matches


def _rule(pattern: str, match_type: str) -> CategoryRule:
    now = datetime.now(UTC)
    return CategoryRule(
        id=uuid.uuid4(),
        household_id=uuid.uuid4(),
        pattern=pattern,
        match_type=match_type,
        category_id=uuid.uuid4(),
        priority=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_exact_is_case_insensitive_and_whole_payee() -> None:
    rule = _rule("Starbucks", "exact")
    assert _rule_matches(rule, "STARBUCKS") is True
    assert _rule_matches(rule, "starbucks") is True
    assert _rule_matches(rule, "STARBUCKS #123") is False  # not the whole payee


def test_contains_matches_substring() -> None:
    rule = _rule("whole foods", "contains")
    assert _rule_matches(rule, "WHOLE FOODS #4432 SEATTLE") is True
    assert _rule_matches(rule, "Trader Joe's") is False


def test_regex_matches_messy_payee() -> None:
    rule = _rule(r"^AMZN Mktp", "regex")
    assert _rule_matches(rule, "AMZN Mktp US*2X4YZ") is True
    assert _rule_matches(rule, "AMAZON.COM") is False


def test_regex_is_case_insensitive() -> None:
    rule = _rule(r"uber\s*eats", "regex")
    assert _rule_matches(rule, "UBER EATS 8842") is True


def test_invalid_regex_never_matches_not_raises() -> None:
    rule = _rule(r"([unclosed", "regex")
    assert _rule_matches(rule, "anything") is False


def test_unknown_match_type_never_matches() -> None:
    rule = _rule("x", "bogus")
    assert _rule_matches(rule, "x") is False


def test_normalize() -> None:
    assert _normalize("  Whole Foods  ") == "WHOLE FOODS"
