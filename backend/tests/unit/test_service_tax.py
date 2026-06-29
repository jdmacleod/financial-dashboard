"""Unit tests for the federal tax-estimate engine.

Expected values are hand-computed from the bracket/standard-deduction tables in
`tax_tables` so they verify the engine logic, not just echo the constants.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import tax_tables
from app.services.tax import (
    alternative_minimum_tax,
    bracket_headroom,
    estimate_federal_tax,
    federal_tax_for,
    marginal_rate_for,
    net_investment_income_tax,
    preferential_tax,
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


def test_preferential_tax_spans_zero_fifteen_twenty() -> None:
    # 2025 Single breakpoints: 0% to 48,350, 15% to 533,400, 20% above.
    bp = tax_tables.CAPITAL_GAINS_BREAKPOINTS[2025][tax_tables.SINGLE]
    # All qualified income sits below the 0% ceiling -> untaxed.
    assert preferential_tax(bp, Decimal("10000"), Decimal("20000")) == Decimal("0")
    # Stacked on 40,000 ordinary: 8,350 fills the 0% room, 11,650 taxed at 15%.
    assert preferential_tax(bp, Decimal("40000"), Decimal("20000")) == Decimal("1747.50")
    # Stacked above the 15% ceiling: a slice at 15%, the rest at 20%.
    #   ordinary 530,000; qualified 10,000 -> 3,400 @15% (to 533,400) + 6,600 @20%.
    assert preferential_tax(bp, Decimal("530000"), Decimal("10000")) == Decimal("1830.00")


def test_estimate_qualified_income_preferential_rate() -> None:
    # Single 2025: wages 80,000 ordinary + 10,000 qualified (LTCG + qual. dividends).
    #   taxable income = 90,000 - 15,750 std = 74,250
    #   ordinary taxable = 64,250; qualified taxable = 10,000
    #   ordinary tax = 1,192.50 + 4,386 + 3,470.50 = 9,049
    #   qualified stacks above 64,250 (> 48,350 zero ceiling) -> all 15% = 1,500
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("80000"),
        qualified_income=Decimal("10000"),
        social_security=Decimal("0"),
    )
    assert est.qualified_income == Decimal("10000")
    assert est.taxable_income == Decimal("74250.00")
    assert est.qualified_tax == Decimal("1500.00")
    assert est.federal_tax == Decimal("10549.00")
    # Marginal/headroom remain ordinary-bracket concepts (Roth conversions are
    # ordinary income), read off ordinary taxable income, not the qualified slice.
    assert est.marginal_rate == 0.22


def test_estimate_qualified_income_raises_taxable_social_security() -> None:
    # Capital gains count toward §86 provisional income, so adding qualified
    # income can push more Social Security into the taxable base.
    base = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("20000"),
        social_security=Decimal("20000"),
    )
    with_gains = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("20000"),
        qualified_income=Decimal("20000"),
        social_security=Decimal("20000"),
    )
    assert with_gains.taxable_social_security > base.taxable_social_security


def test_estimate_qualified_income_defaults_to_zero() -> None:
    # Backward compatibility: omitting qualified_income reproduces the prior result.
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("60000"),
        social_security=Decimal("40000"),
    )
    assert est.qualified_income == Decimal("0")
    assert est.qualified_tax == Decimal("0.00")
    assert est.federal_tax == Decimal("7023.00")  # unchanged from the retiree case


def test_niit_charged_on_lesser_of_nii_and_magi_excess() -> None:
    # Single threshold 200,000. MAGI 250,000 (excess 50,000), NII 30,000:
    #   base = min(30,000, 50,000) = 30,000; tax = 3.8% * 30,000 = 1,140.
    assert net_investment_income_tax(
        tax_tables.SINGLE, Decimal("250000"), Decimal("30000")
    ) == Decimal("1140.000")


def test_niit_zero_below_threshold() -> None:
    # MAGI under the 200,000 single threshold -> no NIIT regardless of NII.
    assert net_investment_income_tax(
        tax_tables.SINGLE, Decimal("150000"), Decimal("20000")
    ) == Decimal("0")


def test_niit_capped_by_magi_excess() -> None:
    # Single MAGI 210,000 (excess 10,000) but NII 50,000: charged on the 10,000
    #   excess, not the full NII. tax = 3.8% * 10,000 = 380.
    assert net_investment_income_tax(
        tax_tables.SINGLE, Decimal("210000"), Decimal("50000")
    ) == Decimal("380.000")


def test_estimate_includes_niit_for_high_investment_income() -> None:
    # Single 2025: 300,000 ordinary + 50,000 qualified, no SS.
    #   MAGI = 350,000; excess over 200,000 = 150,000; NII = 50,000.
    #   NIIT = 3.8% * min(50,000, 150,000) = 1,900.
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("300000"),
        qualified_income=Decimal("50000"),
        social_security=Decimal("0"),
    )
    assert est.net_investment_income_tax == Decimal("1900.00")
    # After-tax nets out both the income tax and the NIIT surtax.
    assert est.after_tax_income == Decimal("350000") - est.federal_tax - Decimal("1900.00")
    # The income-tax effective rate excludes the NIIT surtax.
    assert est.effective_rate == pytest.approx(float(est.federal_tax) / 350000, rel=1e-6)


def test_estimate_no_niit_without_investment_income() -> None:
    # The MFJ retiree (no qualified income) owes no NIIT, and federal_tax is
    # unchanged from before NIIT was added.
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("60000"),
        social_security=Decimal("40000"),
    )
    assert est.net_investment_income_tax == Decimal("0.00")
    assert est.federal_tax == Decimal("7023.00")
    assert est.after_tax_income == Decimal("92977.00")


def test_amt_binds_when_tmt_exceeds_regular_tax() -> None:
    # Single 2025, AMTI 450,000 (income + preference add-backs), regular tax 52,023.
    #   exemption 88,100 (no phaseout below 626,350); AMT base = 361,900.
    #   TMT = 26%*239,100 + 28%*(361,900-239,100) = 62,166 + 34,384 = 96,550.
    #   AMT owed = 96,550 - 52,023 = 44,527.
    assert alternative_minimum_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        amti=Decimal("450000"),
        regular_tax=Decimal("52023"),
    ) == Decimal("44527.00")


def test_amt_exemption_phases_out_2025() -> None:
    # Single 2025, AMTI 800,000 (over the 626,350 phaseout start).
    #   exemption = 88,100 - 25%*(800,000-626,350) = 44,687.50; base = 755,312.50.
    #   TMT = 26%*239,100 + 28%*(755,312.50-239,100) = 62,166 + 144,539.50 = 206,705.50.
    assert alternative_minimum_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        amti=Decimal("800000"),
        regular_tax=Decimal("0"),
    ) == Decimal("206705.50")


def test_amt_2026_obbba_50pct_phaseout() -> None:
    # Single 2026: phaseout starts at 500,000 and runs at 50% (the OBBBA change).
    #   AMTI 700,000 -> exemption = max(90,100 - 50%*200,000, 0) = 0; base = 700,000.
    #   TMT = 26%*244,500 + 28%*(700,000-244,500) = 63,570 + 127,540 = 191,110.
    assert alternative_minimum_tax(
        tax_year=2026,
        filing_status=tax_tables.SINGLE,
        amti=Decimal("700000"),
        regular_tax=Decimal("0"),
    ) == Decimal("191110.00")


def test_amt_zero_when_regular_tax_higher() -> None:
    # No preference items: AMTI below/near the exemption -> TMT under regular tax.
    assert alternative_minimum_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        amti=Decimal("250000"),
        regular_tax=Decimal("52023"),
    ) == Decimal("0")


def test_estimate_includes_amt_with_preference_income() -> None:
    # Single 2025: 250,000 ordinary + 200,000 AMT preference add-backs.
    #   regular tax on 234,250 taxable = 52,023; AMTI = 450,000 -> AMT = 44,527.
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("250000"),
        social_security=Decimal("0"),
        amt_preference_income=Decimal("200000"),
    )
    assert est.federal_tax == Decimal("52023.00")
    assert est.alternative_minimum_tax == Decimal("44527.00")
    # After-tax nets the regular tax and the AMT surtax (no NIIT here).
    assert est.after_tax_income == Decimal("153450.00")


def test_estimate_no_amt_without_preference_income() -> None:
    # Same income, no preference add-backs: the standard-deduction add-back alone
    # never lifts TMT above the regular tax, so AMT is 0.
    est = estimate_federal_tax(
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("250000"),
        social_security=Decimal("0"),
    )
    assert est.alternative_minimum_tax == Decimal("0.00")


def test_qss_uses_mfj_schedule_but_single_ss_base() -> None:
    # QSS brackets/standard deduction mirror MFJ, but §86 base amounts are the
    # "all others" 25k/34k, not MFJ's 32k/44k.
    assert (
        tax_tables.FEDERAL_BRACKETS[2025][tax_tables.QSS]
        == (tax_tables.FEDERAL_BRACKETS[2025][tax_tables.MFJ])
    )
    assert tax_tables.SS_PROVISIONAL_BASE[tax_tables.QSS] == (Decimal("25000"), Decimal("34000"))
