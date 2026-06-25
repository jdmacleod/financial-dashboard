from decimal import Decimal

from pydantic import BaseModel

from app.schemas.household import FilingStatus


class FederalTaxEstimate(BaseModel):
    """A federal income-tax estimate over a set of income components.

    An estimate, not a return: ordinary-income brackets + standard deduction +
    Social Security provisional-income taxation only. No capital-gains preferential
    rates, AMT, NIIT, credits, or itemized deductions.
    """

    tax_year: int
    filing_status: FilingStatus
    ordinary_income: Decimal
    social_security_gross: Decimal
    taxable_social_security: Decimal
    standard_deduction: Decimal
    taxable_income: Decimal
    federal_tax: Decimal
    after_tax_income: Decimal
    effective_rate: float
    marginal_rate: float
