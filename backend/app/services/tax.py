"""Federal income-tax estimate engine.

Pure functions over the year-keyed constants in `tax_tables`. Given a household's
filing status, ordinary income (RMDs, pensions, traditional withdrawals, wages),
and gross Social Security benefits, it estimates federal income tax: it taxes the
includable portion of Social Security (§86 provisional-income rules), subtracts the
standard deduction, and applies the ordinary-income brackets.

Scope is deliberately narrow (see tax_tables docstring). Everything here is an
estimate intended for planning, not tax preparation.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.schemas.tax import FederalTaxEstimate
from app.services import tax_tables

_CENTS = Decimal("0.01")
_HALF = Decimal("0.5")
_MAX_TAXABLE_SS = Decimal("0.85")


def resolve_tax_year(year: int) -> int:
    """Clamp a calendar year to the supported table range.

    Future years (until tables are updated each fall) fall back to the latest
    supported year so estimates keep working rather than erroring.
    """
    years = tax_tables.SUPPORTED_YEARS
    return max(min(year, max(years)), min(years))


def taxable_social_security(
    filing_status: str, other_income: Decimal, ss_benefits: Decimal
) -> Decimal:
    """Includable portion of Social Security benefits under 26 U.S.C. §86.

    `other_income` is all non-SS income counted toward provisional income (here,
    the household's ordinary income). Tax-exempt interest is out of scope.
    """
    if ss_benefits <= 0:
        return Decimal("0")
    base1, base2 = tax_tables.SS_PROVISIONAL_BASE[filing_status]
    provisional = other_income + ss_benefits * _HALF

    if provisional <= base1:
        taxable = Decimal("0")
    elif provisional <= base2:
        taxable = min(ss_benefits * _HALF, (provisional - base1) * _HALF)
    else:
        lower_tier = min(ss_benefits * _HALF, (base2 - base1) * _HALF)
        taxable = min(
            ss_benefits * _MAX_TAXABLE_SS,
            (provisional - base2) * _MAX_TAXABLE_SS + lower_tier,
        )
    return min(taxable, ss_benefits * _MAX_TAXABLE_SS)


def federal_tax_for(brackets: tax_tables.BracketTable, taxable_income: Decimal) -> Decimal:
    """Ordinary income tax for `taxable_income` against an ascending bracket table."""
    if taxable_income <= 0:
        return Decimal("0")
    tax = Decimal("0")
    for i, (lower, rate) in enumerate(brackets):
        if taxable_income <= lower:
            break
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else None
        top = taxable_income if upper is None else min(taxable_income, upper)
        tax += (top - lower) * rate
    return tax


def marginal_rate_for(brackets: tax_tables.BracketTable, taxable_income: Decimal) -> float:
    rate = brackets[0][1]
    for lower, r in brackets:
        if taxable_income >= lower:
            rate = r
        else:
            break
    return float(rate)


def estimate_federal_tax(
    *,
    tax_year: int,
    filing_status: str,
    ordinary_income: Decimal,
    social_security: Decimal,
) -> FederalTaxEstimate:
    """Estimate federal income tax for the given income components and year.

    Raises ValueError for an unsupported year or filing status; callers that
    accept arbitrary years should pass `resolve_tax_year(year)`.
    """
    if tax_year not in tax_tables.FEDERAL_BRACKETS:
        raise ValueError(f"unsupported tax year: {tax_year}")
    if filing_status not in tax_tables.FEDERAL_BRACKETS[tax_year]:
        raise ValueError(f"unsupported filing status: {filing_status}")

    ordinary_income = max(ordinary_income, Decimal("0"))
    social_security = max(social_security, Decimal("0"))

    taxable_ss = taxable_social_security(filing_status, ordinary_income, social_security)
    std_deduction = tax_tables.STANDARD_DEDUCTION[tax_year][filing_status]
    gross_taxable = ordinary_income + taxable_ss
    taxable_income = max(gross_taxable - std_deduction, Decimal("0"))

    brackets = tax_tables.FEDERAL_BRACKETS[tax_year][filing_status]
    federal_tax = federal_tax_for(brackets, taxable_income).quantize(_CENTS, ROUND_HALF_UP)

    # Effective rate is tax over the taxable income that actually entered the
    # return (ordinary + includable SS), not over gross SS.
    rate_base = ordinary_income + taxable_ss
    effective_rate = float(federal_tax / rate_base) if rate_base > 0 else 0.0
    after_tax = (ordinary_income + social_security) - federal_tax

    return FederalTaxEstimate(
        tax_year=tax_year,
        filing_status=filing_status,  # type: ignore[arg-type]
        ordinary_income=ordinary_income,
        social_security_gross=social_security,
        taxable_social_security=taxable_ss.quantize(_CENTS, ROUND_HALF_UP),
        standard_deduction=std_deduction,
        taxable_income=taxable_income.quantize(_CENTS, ROUND_HALF_UP),
        federal_tax=federal_tax,
        after_tax_income=after_tax.quantize(_CENTS, ROUND_HALF_UP),
        effective_rate=effective_rate,
        marginal_rate=marginal_rate_for(brackets, taxable_income),
    )
