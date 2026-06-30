"""State income-tax estimate engine.

Pure functions over the year-keyed constants in `state_tax_tables`. Given a
household's state of residence, filing status, and income components, it estimates
state income tax: it taxes ordinary + qualified income (states tax capital gains
and qualified dividends as ordinary income), subtracts the state standard
deduction, and applies the state bracket schedule (a single bracket for flat-tax
states). Social Security is excluded — none of the modeled states tax it.

Scope and simplifications are documented in `state_tax_tables`. Everything here is
a planning estimate, not tax preparation.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.tax import StateTaxEstimate
from app.services import state_tax_tables, tax_tables

_CENTS = Decimal("0.01")

# Household filing statuses (tax_tables) -> state schedule key. States publish
# single + married-filing-jointly schedules; HoH and MFS approximate to single,
# QSS to married-filing-jointly (mirrors the federal QSS rule).
_FILING_KEY: dict[str, str] = {
    tax_tables.SINGLE: state_tax_tables.SINGLE_KEY,
    tax_tables.HOH: state_tax_tables.SINGLE_KEY,
    tax_tables.MFS: state_tax_tables.SINGLE_KEY,
    tax_tables.MFJ: state_tax_tables.MFJ_KEY,
    tax_tables.QSS: state_tax_tables.MFJ_KEY,
}


def resolve_state_tax_year(year: int) -> int:
    """Clamp a calendar year to the supported state-table range.

    State figures lag the federal ones; until the new year's tables are added,
    future years fall back to the latest supported year so estimates keep working.
    """
    years = state_tax_tables.SUPPORTED_YEARS
    return max(min(year, max(years)), min(years))


def _tax_for_brackets(brackets: state_tax_tables.BracketTable, taxable_income: Decimal) -> Decimal:
    """Income tax for `taxable_income` against an ascending bracket table."""
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


def _marginal_rate(brackets: state_tax_tables.BracketTable, taxable_income: Decimal) -> float:
    rate = brackets[0][1]
    for lower, r in brackets:
        if taxable_income >= lower:
            rate = r
        else:
            break
    return float(rate)


def retirement_exclusion(
    state_code: str, member_ages: Sequence[int], retirement_income: Decimal
) -> Decimal:
    """Retirement-ordinary income a state excludes from its taxable base.

    `retirement_income` is the household's retirement-ordinary income (pensions +
    RMDs) eligible for exclusion. A state with no age gate (Illinois) excludes the
    full amount. For age-gated states (Georgia, New York) each member's per-taxpayer
    cap is added for the highest age tier they meet, and the total is capped at the
    retirement income, so a married couple where both qualify gets the doubled cap.
    Returns 0 for states without a modeled exclusion or with no retirement income.
    """
    spec = state_tax_tables.STATE_RETIREMENT_EXCLUSION.get(state_code)
    income = max(retirement_income, Decimal("0"))
    if spec is None or income <= 0:
        return Decimal("0")
    if not spec.age_gated:
        return income
    total_cap = Decimal("0")
    for age in member_ages:
        for min_age, cap in spec.tiers:  # highest age tier first
            if age >= min_age:
                total_cap += cap
                break
    return min(income, total_cap)


def estimate_state_tax(
    *,
    state: str,
    tax_year: int,
    filing_status: str,
    ordinary_income: Decimal,
    qualified_income: Decimal = Decimal("0"),
    social_security: Decimal = Decimal("0"),
    retirement_income: Decimal = Decimal("0"),
    member_ages: Sequence[int] = (),
) -> StateTaxEstimate:
    """Estimate state income tax for the given income components and year.

    `state` is a two-letter US/DC code (case-insensitive). `ordinary_income` is
    income taxed at ordinary rates; `qualified_income` (capital gains + qualified
    dividends) is taxed as ordinary income at the state level. `social_security`
    is accepted for signature parity with the federal engine but is not taxed by
    any modeled state. `retirement_income` is the pension + RMD portion of ordinary
    income eligible for a state retirement-income exclusion, and `member_ages` are
    the household members' ages (used by the age-gated GA/NY exclusions).

    Always returns a `StateTaxEstimate`:
      - no-income-tax state -> modeled=True, state_tax=0, explanatory note;
      - modeled taxing state -> the computed estimate;
      - any other taxing state -> modeled=False, state_tax=0, "not yet modeled".

    Raises ValueError for an unsupported year or filing status; callers that
    accept arbitrary years should pass `resolve_state_tax_year(year)`.
    """
    if tax_year not in state_tax_tables.STATE_BRACKETS:
        raise ValueError(f"unsupported state tax year: {tax_year}")
    if filing_status not in _FILING_KEY:
        raise ValueError(f"unsupported filing status: {filing_status}")

    code = state.strip().upper()
    zero = Decimal("0.00")

    if code in state_tax_tables.NO_INCOME_TAX_STATES:
        return StateTaxEstimate(
            state=code,
            tax_year=tax_year,
            filing_status=filing_status,  # type: ignore[arg-type]
            modeled=True,
            taxable_income=zero,
            state_tax=zero,
            effective_rate=0.0,
            marginal_rate=0.0,
            note=f"{code} has no state income tax.",
        )

    brackets_by_state = state_tax_tables.STATE_BRACKETS[tax_year]
    if code not in brackets_by_state:
        return StateTaxEstimate(
            state=code,
            tax_year=tax_year,
            filing_status=filing_status,  # type: ignore[arg-type]
            modeled=False,
            taxable_income=zero,
            state_tax=zero,
            effective_rate=0.0,
            marginal_rate=0.0,
            note=f"State income tax for {code} is not yet modeled.",
        )

    key = _FILING_KEY[filing_status]
    brackets = brackets_by_state[code][key]
    std_deduction = state_tax_tables.STATE_STANDARD_DEDUCTION[tax_year][code][key]

    # State base: ordinary + qualified (capital gains/dividends taxed as ordinary),
    # less any retirement-income exclusion and the state standard deduction. Social
    # Security is excluded.
    base = max(ordinary_income, Decimal("0")) + max(qualified_income, Decimal("0"))
    exclusion = retirement_exclusion(code, member_ages, retirement_income)
    taxable_income = max(base - exclusion - std_deduction, Decimal("0"))
    state_tax = _tax_for_brackets(brackets, taxable_income).quantize(_CENTS, ROUND_HALF_UP)

    effective_rate = float(state_tax / base) if base > 0 else 0.0

    return StateTaxEstimate(
        state=code,
        tax_year=tax_year,
        filing_status=filing_status,  # type: ignore[arg-type]
        modeled=True,
        taxable_income=taxable_income.quantize(_CENTS, ROUND_HALF_UP),
        state_tax=state_tax,
        retirement_exclusion=exclusion.quantize(_CENTS, ROUND_HALF_UP),
        effective_rate=effective_rate,
        marginal_rate=_marginal_rate(brackets, taxable_income),
        note=None,
    )
