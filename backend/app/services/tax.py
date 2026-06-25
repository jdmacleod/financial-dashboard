"""Federal income-tax estimate engine.

Pure functions over the year-keyed constants in `tax_tables`. Given a household's
filing status, ordinary income (RMDs, pensions, traditional withdrawals, wages,
business and rental income), qualified income (long-term capital gains and qualified
dividends), and gross Social Security benefits, it estimates federal income tax: it
taxes the includable portion of Social Security (§86 provisional-income rules),
subtracts the standard deduction, applies the ordinary-income brackets, and taxes
qualified income at the preferential 0/15/20 schedule stacked on top.

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


def bracket_headroom(
    brackets: tax_tables.BracketTable, taxable_income: Decimal
) -> tuple[Decimal | None, float | None]:
    """Room left in the bracket containing `taxable_income` before the next rate.

    Returns (room, next_rate): how much more ordinary income (e.g. a Roth
    conversion) fits before crossing into the next bracket, and that next bracket's
    rate. Returns (None, None) when already in the top bracket — no ceiling.
    """
    income = max(taxable_income, Decimal("0"))
    for i, (lower, _rate) in enumerate(brackets):
        upper = brackets[i + 1][0] if i + 1 < len(brackets) else None
        if income >= lower and (upper is None or income < upper):
            if upper is None:
                return None, None
            return upper - income, float(brackets[i + 1][1])
    return None, None


def preferential_tax(
    breakpoints: tax_tables.CapGainsBreakpoints,
    ordinary_taxable: Decimal,
    qualified_taxable: Decimal,
) -> Decimal:
    """Tax on qualified income (LTCG + qualified dividends) at the 0/15/20 schedule.

    Qualified income stacks on top of ordinary taxable income: the slice falling
    below the 0% ceiling is untaxed, the slice up to the 15% ceiling is taxed at
    15%, and the remainder at 20%. `ordinary_taxable` and `qualified_taxable` are
    the post-deduction amounts (their sum is total taxable income).
    """
    if qualified_taxable <= 0:
        return Decimal("0")
    zero_ceiling, fifteen_ceiling = breakpoints
    room_0 = max(zero_ceiling - ordinary_taxable, Decimal("0"))
    at_0 = min(qualified_taxable, room_0)
    room_15 = max(fifteen_ceiling - ordinary_taxable - at_0, Decimal("0"))
    at_15 = min(qualified_taxable - at_0, room_15)
    at_20 = qualified_taxable - at_0 - at_15
    return at_15 * tax_tables.CAPITAL_GAINS_RATES[1] + at_20 * tax_tables.CAPITAL_GAINS_RATES[2]


def bracket_ceiling_for_rate(brackets: tax_tables.BracketTable, rate: Decimal) -> Decimal | None:
    """Taxable-income ceiling at the top of the bracket taxed at `rate`.

    Used by Roth-conversion-ladder planning ("fill to the top of the 12%
    bracket"): returns the taxable income at which that bracket ends (the next
    bracket's lower bound). Returns None when `rate` is the top bracket (no
    ceiling) or isn't present in the table.
    """
    for i, (_lower, r) in enumerate(brackets):
        if r == rate:
            if i + 1 < len(brackets):
                return brackets[i + 1][0]
            return None
    return None


def estimate_federal_tax(
    *,
    tax_year: int,
    filing_status: str,
    ordinary_income: Decimal,
    social_security: Decimal,
    qualified_income: Decimal = Decimal("0"),
) -> FederalTaxEstimate:
    """Estimate federal income tax for the given income components and year.

    `ordinary_income` is all income taxed at ordinary rates (wages, business and
    rental income, pensions, traditional withdrawals/RMDs). `qualified_income` is
    long-term capital gains and qualified dividends, taxed at the preferential
    0/15/20 schedule. `social_security` is gross benefits, taxed via §86.

    Raises ValueError for an unsupported year or filing status; callers that
    accept arbitrary years should pass `resolve_tax_year(year)`.
    """
    if tax_year not in tax_tables.FEDERAL_BRACKETS:
        raise ValueError(f"unsupported tax year: {tax_year}")
    if filing_status not in tax_tables.FEDERAL_BRACKETS[tax_year]:
        raise ValueError(f"unsupported filing status: {filing_status}")

    ordinary_income = max(ordinary_income, Decimal("0"))
    social_security = max(social_security, Decimal("0"))
    qualified_income = max(qualified_income, Decimal("0"))

    # Capital gains and dividends count toward §86 provisional income.
    other_income = ordinary_income + qualified_income
    taxable_ss = taxable_social_security(filing_status, other_income, social_security)
    std_deduction = tax_tables.STANDARD_DEDUCTION[tax_year][filing_status]

    # The standard deduction comes off ordinary income first (qualified income sits
    # "on top"); total taxable income then splits into its ordinary and qualified
    # parts for the two rate schedules.
    gross_taxable = ordinary_income + taxable_ss + qualified_income
    taxable_income = max(gross_taxable - std_deduction, Decimal("0"))
    qualified_taxable = min(qualified_income, taxable_income)
    ordinary_taxable = taxable_income - qualified_taxable

    brackets = tax_tables.FEDERAL_BRACKETS[tax_year][filing_status]
    breakpoints = tax_tables.CAPITAL_GAINS_BREAKPOINTS[tax_year][filing_status]
    ordinary_tax = federal_tax_for(brackets, ordinary_taxable)
    qualified_tax = preferential_tax(breakpoints, ordinary_taxable, qualified_taxable)
    federal_tax = (ordinary_tax + qualified_tax).quantize(_CENTS, ROUND_HALF_UP)

    # Roth-conversion headroom and the marginal rate are about ordinary income (a
    # conversion adds ordinary income), so they read off the ordinary taxable base.
    room, next_rate = bracket_headroom(brackets, ordinary_taxable)

    # Effective rate is tax over the income that actually entered the return
    # (ordinary + includable SS + qualified), not over gross SS.
    rate_base = ordinary_income + taxable_ss + qualified_income
    effective_rate = float(federal_tax / rate_base) if rate_base > 0 else 0.0
    after_tax = (ordinary_income + social_security + qualified_income) - federal_tax

    return FederalTaxEstimate(
        tax_year=tax_year,
        filing_status=filing_status,  # type: ignore[arg-type]
        ordinary_income=ordinary_income,
        qualified_income=qualified_income,
        social_security_gross=social_security,
        taxable_social_security=taxable_ss.quantize(_CENTS, ROUND_HALF_UP),
        standard_deduction=std_deduction,
        taxable_income=taxable_income.quantize(_CENTS, ROUND_HALF_UP),
        federal_tax=federal_tax,
        qualified_tax=qualified_tax.quantize(_CENTS, ROUND_HALF_UP),
        after_tax_income=after_tax.quantize(_CENTS, ROUND_HALF_UP),
        effective_rate=effective_rate,
        marginal_rate=marginal_rate_for(brackets, ordinary_taxable),
        roth_conversion_room=room.quantize(_CENTS, ROUND_HALF_UP) if room is not None else None,
        next_bracket_rate=next_rate,
    )
