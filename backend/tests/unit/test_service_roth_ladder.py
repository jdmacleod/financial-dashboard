from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.roth_ladder import project_roth_ladder

# A member born 1970 has an RMD start age of 75 (SECURE 2.0). Retiring at 62
# gives gap years 62..74 (13 years). With zero growth and no other income the
# yearly conversion is deterministic, which makes the math hand-checkable.
_DOB = date(1970, 6, 15)


def _ladder(**overrides: object):
    kwargs: dict[str, object] = {
        "dob": _DOB,
        "filing_status": "single",
        "pretax_start": Decimal("1000000"),
        "annual_return": Decimal("0"),
        "retirement_age": 62,
        "horizon_age": 90,
        "ceiling_rate": Decimal("0.12"),
        "income_by_year": {},
    }
    kwargs.update(overrides)
    return project_roth_ladder(**kwargs)  # type: ignore[arg-type]


def test_unavailable_without_prerequisites() -> None:
    assert _ladder(dob=None).available is False
    assert _ladder(filing_status=None).available is False
    no_pretax = _ladder(pretax_start=Decimal("0"))
    assert no_pretax.available is False
    assert no_pretax.note is not None


def test_fills_to_bracket_ceiling() -> None:
    # 2032 resolves to the 2026 table: single std deduction 16,100, top of the
    # 12% bracket at 50,400 taxable income. With no other income, the conversion
    # brings taxable income to 50,400 -> gross conversion 50,400 + 16,100 = 66,500.
    res = _ladder()
    assert res.available is True
    assert res.gap_start_year == 2032
    assert res.gap_start_age == 62
    assert res.rmd_start_age == 75
    assert len(res.years) == 13  # ages 62..74

    first = res.years[0]
    assert first.year == 2032
    assert first.age == 62
    assert first.conversion == Decimal("66500.00")
    # tax on 50,400 taxable: 10% * 12,400 + 12% * 38,000 = 5,800.
    assert first.federal_tax == Decimal("5800.00")
    # Zero growth -> pretax falls by exactly the conversion each year.
    assert first.pretax_balance == Decimal("933500.00")

    # 13 identical conversions (no growth, no other income).
    assert res.total_converted == Decimal("864500.00")


def test_conversions_cut_lifetime_tax_with_growth() -> None:
    # With real growth, an un-converted balance compounds into large RMDs taxed
    # well above the 12% conversion bracket. Filling 12% in the gap years moves
    # those dollars out cheaply, so lifetime federal tax is lower with conversions.
    res = _ladder(pretax_start=Decimal("2000000"), annual_return=Decimal("0.07"))
    assert res.total_converted > 0
    assert res.lifetime_tax_without > res.lifetime_tax_with
    assert res.lifetime_tax_saved == res.lifetime_tax_without - res.lifetime_tax_with
    assert res.lifetime_tax_saved > 0


def test_aggressive_conversion_can_cost_more_without_growth() -> None:
    # Honesty check: with zero growth and no other income the slow RMDs would
    # sit in the standard deduction / 10% bracket, so paying 12% to fill the
    # bracket now is a net loss. The tool must surface that, not assume the
    # ladder always wins.
    res = _ladder()  # 0% growth, no other income
    assert res.total_converted > 0
    assert res.lifetime_tax_saved < 0
    assert res.lifetime_tax_with > res.lifetime_tax_without


def test_other_income_reduces_conversion_room() -> None:
    # 30,000 of ordinary income in 2032 fills part of the bracket, leaving
    # 66,500 - 30,000 = 36,500 of conversion room that year.
    res = _ladder(income_by_year={2032: (Decimal("30000"), Decimal("0"))})
    assert res.years[0].conversion == Decimal("36500.00")
    assert res.years[0].ordinary_income == Decimal("30000")


def test_no_gap_years_when_retiring_at_rmd_age() -> None:
    # Retiring at 75 (the RMD start age) leaves no gap years: nothing converts and
    # lifetime tax is identical with or without the (empty) ladder.
    res = _ladder(retirement_age=75)
    assert res.available is True
    assert res.years == []
    assert res.total_converted == Decimal("0.00")
    assert res.lifetime_tax_saved == Decimal("0.00")
