from decimal import Decimal

from pydantic import BaseModel

from app.schemas.household import FilingStatus


class FederalTaxEstimate(BaseModel):
    """A federal income-tax estimate over a set of income components.

    An estimate, not a return: ordinary-income brackets + standard deduction +
    Social Security provisional-income taxation + the preferential long-term
    capital-gains / qualified-dividend schedule, plus the §1411 net investment
    income tax (NIIT). No AMT, credits, itemized deductions, or state income tax.
    """

    tax_year: int
    filing_status: FilingStatus
    ordinary_income: Decimal
    # Long-term capital gains + qualified dividends, taxed at the 0/15/20 schedule.
    qualified_income: Decimal = Decimal("0")
    social_security_gross: Decimal
    taxable_social_security: Decimal
    standard_deduction: Decimal
    taxable_income: Decimal
    federal_tax: Decimal
    # Portion of `federal_tax` attributable to qualified income (preferential rates).
    qualified_tax: Decimal = Decimal("0")
    # §1411 net investment income tax: 3.8% on the lesser of net investment income
    # (here, qualified income) and the excess of MAGI over the statutory threshold.
    net_investment_income_tax: Decimal = Decimal("0")
    after_tax_income: Decimal
    effective_rate: float
    marginal_rate: float
    # Roth-conversion planning: how much more ordinary income (a pretax -> Roth
    # conversion) fits before crossing into the next federal bracket, and that
    # next bracket's rate. None when already in the top bracket.
    roth_conversion_room: Decimal | None = None
    next_bracket_rate: float | None = None


class StateTaxEstimate(BaseModel):
    """A state income-tax estimate keyed off the household's state of residence.

    A planning estimate, not a return. Applies the state's bracket schedule (a
    single bracket for flat-tax states) to ordinary + qualified income less the
    state standard deduction. ``modeled`` is False for a taxing state whose
    schedule isn't in the table yet (``state_tax`` is then 0 with an explanatory
    ``note``); it is True both for modeled taxing states and for the nine states
    with no individual income tax (where ``state_tax`` is a real 0).

    Documented simplifications: states tax long-term capital gains and qualified
    dividends as ordinary income (no preferential state schedule); Social Security
    is excluded (none of the modeled states tax it); and state-specific
    retirement-income exclusions (e.g. Illinois's full exclusion, Georgia's
    age-based exclusion, New York's $20k pension exclusion) are not applied.
    """

    state: str
    tax_year: int
    filing_status: FilingStatus
    modeled: bool
    taxable_income: Decimal
    state_tax: Decimal
    effective_rate: float
    marginal_rate: float
    note: str | None = None
