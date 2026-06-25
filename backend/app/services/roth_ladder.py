"""Roth-conversion-ladder analysis for the FIRE gap years.

A pure simulation (no DB) of the standard "conversion ladder" strategy: in the
low-income years between retirement and the RMD start age, convert pretax money
to Roth up to the top of a target federal bracket each year. Filling those low
brackets now shrinks the pretax balance, which lowers future required minimum
distributions and the tax on them. The headline is lifetime federal tax with the
conversions vs. without.

Scope: an estimate over a single pretax bucket plus the household's per-year
ordinary and Social Security income. It does not simulate the full retirement
portfolio drawdown (that is the FIRE projection's job) and ignores state tax, the
second-order feedback of a conversion onto taxable Social Security, and qualified
investment income.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.services import tax_tables
from app.services.age import age_in_year, rmd_start_age
from app.services.rmd import uniform_lifetime_divisor
from app.services.tax import bracket_ceiling_for_rate, estimate_federal_tax, resolve_tax_year

_CENTS = Decimal("0.01")


@dataclass
class RothLadderYearRow:
    year: int
    age: int
    pretax_balance: Decimal  # after this year's conversion and any RMD
    ordinary_income: Decimal  # baseline income streams + RMD, pre-conversion
    social_security: Decimal
    conversion: Decimal
    federal_tax: Decimal  # this year's total federal tax (incl. the conversion)


@dataclass
class RothLadderResult:
    available: bool
    note: str | None
    ceiling_rate: Decimal
    gap_start_year: int | None
    gap_start_age: int | None
    rmd_start_age: int | None
    horizon_age: int
    total_converted: Decimal
    lifetime_tax_with: Decimal
    lifetime_tax_without: Decimal
    lifetime_tax_saved: Decimal
    years: list[RothLadderYearRow]


def _unavailable(note: str, ceiling_rate: Decimal, horizon_age: int) -> RothLadderResult:
    zero = Decimal("0")
    return RothLadderResult(
        available=False,
        note=note,
        ceiling_rate=ceiling_rate,
        gap_start_year=None,
        gap_start_age=None,
        rmd_start_age=None,
        horizon_age=horizon_age,
        total_converted=zero,
        lifetime_tax_with=zero,
        lifetime_tax_without=zero,
        lifetime_tax_saved=zero,
        years=[],
    )


def project_roth_ladder(
    *,
    dob: date | None,
    filing_status: str | None,
    pretax_start: Decimal,
    annual_return: Decimal,
    retirement_age: int,
    horizon_age: int,
    ceiling_rate: Decimal,
    income_by_year: dict[int, tuple[Decimal, Decimal]],
) -> RothLadderResult:
    """Simulate the conversion ladder and the with/without lifetime-tax comparison.

    `income_by_year` maps each calendar year to ``(ordinary_income, social_security)``
    the household receives independent of conversions (pensions, claimed Social
    Security, etc.). The simulation grows a single pretax bucket at `annual_return`,
    takes RMDs from the SECURE 2.0 start age, and in the gap years before that age
    converts up to the top of the `ceiling_rate` bracket.
    """
    if dob is None:
        return _unavailable(
            "Set the member's date of birth to model conversions.", ceiling_rate, horizon_age
        )
    if filing_status is None:
        return _unavailable(
            "Set the household filing status to model conversions.", ceiling_rate, horizon_age
        )
    if pretax_start <= 0:
        return _unavailable("No pretax retirement balance to convert.", ceiling_rate, horizon_age)

    start_age = rmd_start_age(dob)
    retire_year = dob.year + retirement_age
    horizon_year = dob.year + horizon_age

    def simulate(convert: bool) -> tuple[Decimal, Decimal, list[RothLadderYearRow]]:
        pretax = pretax_start
        lifetime_tax = Decimal("0")
        total_converted = Decimal("0")
        rows: list[RothLadderYearRow] = []
        for year in range(retire_year, horizon_year + 1):
            age = age_in_year(dob, year)
            if age is None:
                continue
            pretax *= Decimal(1) + annual_return
            ordinary_base, ss = income_by_year.get(year, (Decimal("0"), Decimal("0")))

            rmd = Decimal("0")
            if start_age is not None and age >= start_age and pretax > 0:
                divisor = uniform_lifetime_divisor(age)
                if divisor is not None:
                    rmd = (pretax / divisor).quantize(_CENTS)
                    pretax -= rmd

            conversion = Decimal("0")
            in_gap = start_age is not None and age < start_age
            if convert and in_gap and pretax > 0:
                tax_year = resolve_tax_year(year)
                ceiling = bracket_ceiling_for_rate(
                    tax_tables.FEDERAL_BRACKETS[tax_year][filing_status], ceiling_rate
                )
                if ceiling is not None:
                    base = estimate_federal_tax(
                        tax_year=tax_year,
                        filing_status=filing_status,
                        ordinary_income=ordinary_base + rmd,
                        social_security=ss,
                    )
                    # Convert enough to bring TAXABLE income to the bracket ceiling.
                    # A conversion adds dollar-for-dollar to ordinary income, so the
                    # headroom is measured against pre-deduction taxable income
                    # (unfloored) — when current income is below the standard
                    # deduction, the unused deduction is extra conversion room. SS
                    # provisional feedback from the conversion is ignored (an
                    # estimate, and SS is usually unclaimed in the gap years).
                    pre_taxable = (
                        base.ordinary_income
                        + base.taxable_social_security
                        - base.standard_deduction
                    )
                    headroom = ceiling - pre_taxable
                    if headroom > 0:
                        conversion = min(headroom, pretax).quantize(_CENTS)
                        pretax -= conversion
                        total_converted += conversion

            est = estimate_federal_tax(
                tax_year=resolve_tax_year(year),
                filing_status=filing_status,
                ordinary_income=ordinary_base + rmd + conversion,
                social_security=ss,
            )
            lifetime_tax += est.federal_tax

            if convert:
                rows.append(
                    RothLadderYearRow(
                        year=year,
                        age=age,
                        pretax_balance=pretax.quantize(_CENTS),
                        ordinary_income=ordinary_base + rmd,
                        social_security=ss,
                        conversion=conversion,
                        federal_tax=est.federal_tax,
                    )
                )
        return lifetime_tax, total_converted, rows

    tax_with, total_converted, rows = simulate(convert=True)
    tax_without, _, _ = simulate(convert=False)

    # The table focuses on the gap years where conversions actually happen; the
    # post-RMD years fold into the lifetime-tax comparison.
    gap_rows = [r for r in rows if start_age is None or r.age < start_age]

    return RothLadderResult(
        available=True,
        note=None,
        ceiling_rate=ceiling_rate,
        gap_start_year=retire_year,
        gap_start_age=retirement_age,
        rmd_start_age=start_age,
        horizon_age=horizon_age,
        total_converted=total_converted.quantize(_CENTS),
        lifetime_tax_with=tax_with.quantize(_CENTS),
        lifetime_tax_without=tax_without.quantize(_CENTS),
        lifetime_tax_saved=(tax_without - tax_with).quantize(_CENTS),
        years=gap_rows,
    )
