from decimal import Decimal

from pydantic import BaseModel

from app.schemas.household import FilingStatus


class FederalTaxEstimate(BaseModel):
    """A federal income-tax estimate over a set of income components.

    An estimate, not a return: ordinary-income brackets + standard deduction +
    Social Security provisional-income taxation + the preferential long-term
    capital-gains / qualified-dividend schedule. No AMT, NIIT, credits, itemized
    deductions, or state income tax.
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
    after_tax_income: Decimal
    effective_rate: float
    marginal_rate: float
    # Roth-conversion planning: how much more ordinary income (a pretax -> Roth
    # conversion) fits before crossing into the next federal bracket, and that
    # next bracket's rate. None when already in the top bracket.
    roth_conversion_room: Decimal | None = None
    next_bracket_rate: float | None = None
