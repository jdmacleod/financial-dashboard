"""Unit tests for the state income-tax estimate engine.

Expected values are hand-computed from the bracket/standard-deduction tables in
`state_tax_tables` so they verify the engine logic, not just echo the constants.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services import tax_tables
from app.services.state_tax import estimate_state_tax, resolve_state_tax_year


def test_california_graduated_single_2025() -> None:
    # CA single 2025, 100,000 ordinary: taxable = 100,000 - 5,540 std = 94,460.
    #   1%*10,756 + 2%*(25,499-10,756) + 4%*(40,245-25,499) + 6%*(55,866-40,245)
    #   + 8%*(70,606-55,866) + 9.3%*(94,460-70,606)
    #   = 107.56 + 294.86 + 589.84 + 937.26 + 1,179.20 + 2,218.422 = 5,327.14
    est = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert est.modeled is True
    assert est.taxable_income == Decimal("94460.00")
    assert est.state_tax == Decimal("5327.14")
    assert est.marginal_rate == 0.093
    assert est.note is None


def test_new_york_graduated_mfj_2025() -> None:
    # NY MFJ 2025, 100,000 ordinary: taxable = 100,000 - 16,050 std = 83,950.
    #   4%*17,150 + 4.5%*(23,600-17,150) + 5.25%*(27,900-23,600) + 5.5%*(83,950-27,900)
    #   = 686.00 + 290.25 + 225.75 + 3,082.75 = 4,284.75
    est = estimate_state_tax(
        state="NY",
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("100000"),
    )
    assert est.taxable_income == Decimal("83950.00")
    assert est.state_tax == Decimal("4284.75")
    assert est.marginal_rate == 0.055


def test_georgia_flat_5_39_2025() -> None:
    # GA flat 5.39%: taxable = 100,000 - 12,000 std = 88,000; tax = 4,743.20.
    est = estimate_state_tax(
        state="GA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert est.state_tax == Decimal("4743.20")
    assert est.marginal_rate == 0.0539


def test_illinois_flat_4_95_uses_personal_exemption_2025() -> None:
    # IL flat 4.95%, personal-exemption subtraction 2,850 (single):
    #   taxable = 100,000 - 2,850 = 97,150; tax = 97,150 * 0.0495 = 4,808.93.
    est = estimate_state_tax(
        state="IL",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert est.taxable_income == Decimal("97150.00")
    assert est.state_tax == Decimal("4808.93")
    assert est.marginal_rate == 0.0495


def test_qualified_income_taxed_as_ordinary_at_state_level() -> None:
    # No state preferential rate: 60,000 ordinary + 40,000 qualified taxes the same
    # as 100,000 ordinary for the same filing status.
    split = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("60000"),
        qualified_income=Decimal("40000"),
    )
    combined = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert split.state_tax == combined.state_tax


def test_social_security_excluded_from_state_base() -> None:
    # None of the modeled states tax Social Security: passing SS doesn't change tax.
    without_ss = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("50000"),
    )
    with_ss = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("50000"),
        social_security=Decimal("30000"),
    )
    assert with_ss.state_tax == without_ss.state_tax


def test_hoh_maps_to_single_schedule() -> None:
    # No separate state HoH schedule is modeled: HoH uses the single schedule.
    hoh = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.HOH,
        ordinary_income=Decimal("100000"),
    )
    single = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert hoh.state_tax == single.state_tax


def test_qss_maps_to_mfj_schedule() -> None:
    qss = estimate_state_tax(
        state="NY",
        tax_year=2025,
        filing_status=tax_tables.QSS,
        ordinary_income=Decimal("100000"),
    )
    mfj = estimate_state_tax(
        state="NY",
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("100000"),
    )
    assert qss.state_tax == mfj.state_tax


def test_no_income_tax_state_returns_zero_modeled() -> None:
    est = estimate_state_tax(
        state="tx",  # case-insensitive
        tax_year=2025,
        filing_status=tax_tables.MFJ,
        ordinary_income=Decimal("250000"),
    )
    assert est.state == "TX"
    assert est.modeled is True
    assert est.state_tax == Decimal("0.00")
    assert est.marginal_rate == 0.0
    assert est.note is not None and "no state income tax" in est.note


def test_unmodeled_taxing_state_returns_zero_unmodeled() -> None:
    est = estimate_state_tax(
        state="VA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("100000"),
    )
    assert est.modeled is False
    assert est.state_tax == Decimal("0.00")
    assert est.note is not None and "not yet modeled" in est.note


def test_no_tax_when_below_standard_deduction() -> None:
    est = estimate_state_tax(
        state="CA",
        tax_year=2025,
        filing_status=tax_tables.SINGLE,
        ordinary_income=Decimal("4000"),  # below the 5,540 std deduction
    )
    assert est.taxable_income == Decimal("0.00")
    assert est.state_tax == Decimal("0.00")
    assert est.effective_rate == 0.0


def test_resolve_state_tax_year_clamps() -> None:
    assert resolve_state_tax_year(2025) == 2025
    assert resolve_state_tax_year(2026) == 2025  # future -> latest supported
    assert resolve_state_tax_year(2020) == 2025  # past -> earliest supported


def test_rejects_unsupported_year_and_status() -> None:
    with pytest.raises(ValueError):
        estimate_state_tax(
            state="CA",
            tax_year=1999,
            filing_status=tax_tables.SINGLE,
            ordinary_income=Decimal("100000"),
        )
    with pytest.raises(ValueError):
        estimate_state_tax(
            state="CA",
            tax_year=2025,
            filing_status="bogus",
            ordinary_income=Decimal("100000"),
        )
