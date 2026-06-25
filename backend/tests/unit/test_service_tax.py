"""Unit tests for the federal tax-estimate engine.

Expected values are hand-computed from the bracket/standard-deduction tables in
`tax_tables` so they verify the engine logic, not just echo the constants.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import tax_tables
from app.services.tax import (
    bracket_headroom,
    estimate_federal_tax,
    federal_tax_for,
    marginal_rate_for,
    resolve_tax_year,
    taxable_social_security,
)


def test_federal_tax_for_single_2025_50k() -> None:
    # 2025 single, taxable income 50,000:
    #   10% * 11,925            = 1,192.50
    #   12% * (48,475-11,925)   = 4,386.00
    #   22% * (50,000-48,475)   =   335.50
    brackets = tax_tables.FEDERAL_BRACKETS[2025][tax_tables.SINGLE]
    assert federal_tax_for(brackets, Decimal("50000")) == Decimal("5914.00")


def test_federal_tax_for_zero_and_negative() -> None:
    brackets = tax_tables.FEDERAL_BRACKETS[2025][tax_tables.SINGLE]
    assert federal_tax_for(brackets, Decimal("0")) == Decimal("0")
    assert federal_tax_for(brackets, Decimal("-100")) == Decimal("0")


def test_marginal_rate_for() -> None:
    brackets = tax_tables.FEDERAL_BRACKETS[2025][tax_tables.SINGLE]
    assert marginal_rate_for(brackets, Decimal("50000")) == 0.22
    assert marginal_rate_for(brackets, Decimal("0")) == 0.10
    assert marginal_rate_for(brackets, Decimal("700000")) == 0.37


def test_bracket_headroom_single_2025() -> None:
    brackets = tax_tables.FEDERAL_BRACKETS[2025][tax_tables.SINGLE]
    # 50,000 sits in the 22% bracket (48,475-103,350): room to 24% = 53,350.
    assert bracket_headroom(brackets, Decimal("50000")) == (Decimal("53350"), 0.24)
    # 0 sits in the 10% bracket (0-11,925): room to 12% = 11,925.
    assert bracket_headroom(brackets, Decimal("0")) == (Decimal("11925"), 0.12)
    # On a threshold belongs to the higher bracket (48,475 -> 22% bracket).
    assert bracket_headroom(brackets, Decimal("48475")) == (Decimal("54875"), 0.24)


def test_bracket_headroom_top_bracket_has_none() -> None:
    brackets = tax_tables.FEDERAL_BRACKETS[2025][tax_tables.SINGLE]
    assert bracket_headroom(brackets, Decimal("700000")) == (None, None)


def test_taxable_ss_below_base_is_zero() -> None:
    # provisional = 10,000 + 5,000 = 15,000 <= 25,000 base1 (single)
    assert taxable_social_security(
        tax_tables.SINGLE, Decimal("10000"), Decimal("10000")
    ) == Decimal("0")


def test_taxable_ss_fifty_percent_tier() -> None:
    # single, other 20,000 + SS 20,000: provisional = 30,000 (between 25k and 34k)
    #   taxable = min(0.5*20,000, 0.5*(30,000-25,000)) = min(10,000, 2,500) = 2,500
    assert taxable_social_security(
        tax_tables.SINGLE, Decimal("20000"), Decimal("20000")
    ) == Decimal("2500.0")


def test_taxable_ss_eighty_five_percent_cap() -> None:
    # single, other 40,000 + SS 20,000: provisional = 50,000 (> 34,000)
    #   lower_tier = min(10,000, 0.5*(34k-25k)=4,500) = 4,500
    #   taxable = min(0.85*20,000=17,000, 0.85*16,000+4,500=18,100) = 17,000 (capped)
    assert taxable_social_security(
        tax_tables.SINGLE, Decimal("40000"), Decimal("20000")
    ) == Decimal("17000.0")


def test_taxable_ss_no_benefits() -> None:
    assert taxable_social_security(tax_tables.MFJ, Decimal("80000"), Decimal("0")) == Decimal("0")


def test_estimate_mfj_retiree_2025() -> None:
    # MFJ 2025: ordinary 60,000 (RMD+pension) + SS 40,000.
    #   provisional = 60,000 + 20,000 = 80,000 (> 44,000 MFJ base2)
    #   lower_tier = min(20,000, 0.5*(44k-32k)=6,000) = 6,000
    #   taxable_ss = min(0.85*40,000=34,000, 0.85*36,000+6,000=36,600) = 34,000 (cap)
    #   taxable income = 60,000 + 34,000 - 31,500 (std) = 62,500
    #   tax = 10%*23,850 + 12%*(62,500-23,850) = 2,385 + 4,638 = 7,023
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("60000"),
        social_security=Decimal("40000"),
    )
    assert est.taxable_social_security == Decimal("34000.00")
    assert est.taxable_income == Decimal("62500.00")
    assert est.federal_tax == Decimal("7023.00")
    assert est.marginal_rate == 0.12
    assert est.after_tax_income == Decimal("92977.00")  # 100,000 - 7,023
    assert est.effective_rate == pytest.approx(7023 / 94000, rel=1e-6)
    # Roth headroom: taxable income 62,500 is in the 12% bracket (top 96,950 MFJ),
    # so 34,450 more can be converted before the 22% bracket.
    assert est.roth_conversion_room == Decimal("34450.00")
    assert est.next_bracket_rate == 0.22


def test_estimate_no_tax_when_below_standard_deduction() -> None:
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("10000"),
        social_security=Decimal("0"),
    )
    assert est.taxable_income == Decimal("0.00")
    assert est.federal_tax == Decimal("0.00")
    assert est.effective_rate == 0.0


def test_estimate_rejects_unsupported_year_and_status() -> None:
    with pytest.raises(ValueError):
        estimate_federal_tax(
            tax_year=1999,
            filing_status=tax_tables.SINGLE,
            ordinary_income=Decimal("50000"),
            social_security=Decimal("0"),
        )
    with pytest.raises(ValueError):
        estimate_federal_tax(
            tax_year=2025,
            filing_status="bogus",
            ordinary_income=Decimal("50000"),
            social_security=Decimal("0"),
        )


def test_resolve_tax_year_clamps() -> None:
    assert resolve_tax_year(2025) == 2025
    assert resolve_tax_year(2026) == 2026
    assert resolve_tax_year(2030) == 2026  # future -> latest supported
    assert resolve_tax_year(2010) == 2025  # past -> earliest supported


def test_qss_uses_mfj_schedule_but_single_ss_base() -> None:
    # QSS brackets/standard deduction mirror MFJ, but §86 base amounts are the
    # "all others" 25k/34k, not MFJ's 32k/44k.
    assert (
        tax_tables.FEDERAL_BRACKETS[2025][tax_tables.QSS]
        == (tax_tables.FEDERAL_BRACKETS[2025][tax_tables.MFJ])
    )
    assert tax_tables.SS_PROVISIONAL_BASE[tax_tables.QSS] == (Decimal("25000"), Decimal("34000"))
