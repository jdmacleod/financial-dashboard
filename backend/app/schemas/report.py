import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BudgetPeriod = Literal["monthly", "annual"]


class PensionAnnotation(BaseModel):
    account_id: uuid.UUID
    nickname: str
    monthly_benefit: Decimal | None
    eligibility_age: int | None
    eligibility_date: date | None
    # Present value used in the net-worth report. Accounts for time-to-eligibility,
    # COLA growth, a finite life annuity, and the survivor benefit (see
    # app.services.pension_valuation). None when no benefit estimate is recorded.
    estimated_pv: Decimal | None


class NetWorthBreakdown(BaseModel):
    checking_savings: Decimal
    investment: Decimal
    retirement: Decimal
    real_estate: Decimal
    hsa: Decimal
    other_assets: Decimal
    mortgage: Decimal
    other_liabilities: Decimal


class NetWorthPoint(BaseModel):
    date: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    breakdown: NetWorthBreakdown


class NetWorthReport(BaseModel):
    series: list[NetWorthPoint]
    current: NetWorthPoint | None
    pension_annotations: list[PensionAnnotation] = []


class CashFlowPeriod(BaseModel):
    period: str
    income: Decimal
    expenses: Decimal
    net: Decimal
    savings_rate: float


class CashFlowTotals(BaseModel):
    income: Decimal
    expenses: Decimal
    net: Decimal
    savings_rate: float


class RetirementIncomeBreakdown(BaseModel):
    """Period totals for retirement-specific income streams, broken out as
    labeled buckets. ``has_data`` lets the UI hide the panel for households with
    no retirement income (e.g. anyone not yet drawing benefits)."""

    social_security: Decimal
    pension: Decimal
    rmd: Decimal
    total: Decimal
    has_data: bool


class CashFlowReport(BaseModel):
    series: list[CashFlowPeriod]
    totals: CashFlowTotals
    retirement_income: RetirementIncomeBreakdown


class SpendingCategoryItem(BaseModel):
    category_id: uuid.UUID | None
    name: str
    amount: Decimal
    percentage: float
    transaction_count: int
    has_children: bool


class SpendingByCategoryReport(BaseModel):
    total: Decimal
    categories: list[SpendingCategoryItem]


class BudgetVsActualsItem(BaseModel):
    category_id: uuid.UUID
    name: str
    budget: Decimal
    actual: Decimal
    remaining: Decimal
    percentage_used: float
    period: BudgetPeriod = "monthly"


class BudgetVsActualsReport(BaseModel):
    period: str
    categories: list[BudgetVsActualsItem]


class BudgetTrendPoint(BaseModel):
    period: str
    budget: Decimal
    actual: Decimal
    # budget - actual; positive = under budget, negative = over budget.
    variance: Decimal


class BudgetTrendReport(BaseModel):
    series: list[BudgetTrendPoint]
    total_budget: Decimal
    total_actual: Decimal
    total_variance: Decimal


class SavingsRatePoint(BaseModel):
    period: str
    income: Decimal
    expenses: Decimal
    # income - expenses for the period (can be negative in a deficit month).
    savings: Decimal
    savings_rate: float
    # Trailing 3-month average of savings_rate, smoothing lumpy months.
    rolling_rate: float


class SavingsRateReport(BaseModel):
    series: list[SavingsRatePoint]
    # Aggregate rate over the whole window: total savings / total income.
    average_rate: float
    best_period: str | None
    worst_period: str | None


class PropertyExpenseItem(BaseModel):
    category_id: uuid.UUID | None
    name: str
    amount: Decimal


class PropertyMonthlyPoint(BaseModel):
    period: str
    income: Decimal
    expenses: Decimal
    net: Decimal


class PropertyPnLPeriod(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: date = Field(alias="from")
    to: date


class PropertyPnLReport(BaseModel):
    property_id: uuid.UUID
    nickname: str
    address: str
    period: PropertyPnLPeriod
    gross_income: Decimal
    total_expenses: Decimal
    net_income: Decimal
    net_yield_pct: float | None
    expense_breakdown: list[PropertyExpenseItem]
    monthly_series: list[PropertyMonthlyPoint]


class EstateExposureEntity(BaseModel):
    """One titling bucket in the estate-exposure report. ``entity_id`` is None
    for directly-owned assets (no ownership entity), which sit in the taxable
    estate by default.
    """

    entity_id: uuid.UUID | None
    entity_name: str | None
    entity_type: str | None
    is_in_taxable_estate: bool
    assets: Decimal
    liabilities: Decimal
    net_value: Decimal


class EstateExposureReport(BaseModel):
    as_of: date
    # Net value (assets - liabilities) of holdings that sit inside the taxable
    # estate: directly-owned assets plus revocable-trust-titled assets.
    gross_taxable_estate: Decimal
    # Net value held outside the taxable estate (ILIT / irrevocable trust / CRT).
    excluded_from_estate: Decimal
    total_net_worth: Decimal
    exemption_per_person: Decimal
    # 1 for a single filer, 2 for a married couple (portability), derived from
    # the count of primary/partner members.
    exemption_holders: int
    applicable_exemption: Decimal
    # max(0, gross_taxable_estate - applicable_exemption).
    taxable_overage: Decimal
    estimated_federal_estate_tax: Decimal
    federal_estate_tax_rate: float
    entities: list[EstateExposureEntity]


class DashboardNetWorth(BaseModel):
    current: Decimal
    change_30d: Decimal
    change_30d_pct: float | None


class DashboardCashFlow(BaseModel):
    income: Decimal
    expenses: Decimal
    net: Decimal


class DashboardSpendingCategory(BaseModel):
    category_id: uuid.UUID | None
    name: str
    amount: Decimal


class DashboardBudgetAlert(BaseModel):
    category: str
    used_pct: float


class DashboardAccountsSummary(BaseModel):
    total_assets: Decimal
    total_liabilities: Decimal


class DashboardResponse(BaseModel):
    net_worth: DashboardNetWorth
    cash_flow_mtd: DashboardCashFlow
    top_spending_categories: list[DashboardSpendingCategory]
    budget_alerts: list[DashboardBudgetAlert]
    accounts_summary: DashboardAccountsSummary


class MemberRequiredDistribution(BaseModel):
    member_id: uuid.UUID
    display_name: str
    date_of_birth: date | None
    current_age: int | None
    rmd_start_age: int | None
    rmd_start_year: int | None
    # True once the member has reached RMD age and a distribution is required
    # this year.
    has_started: bool
    # Prior-year-end pretax balance the RMD is computed from, and the snapshot
    # date that supplied it. None when no prior-year snapshot exists.
    pretax_balance: Decimal | None
    balance_as_of: date | None
    # IRS Uniform Lifetime divisor for this year's age, and the resulting RMD.
    divisor: Decimal | None
    rmd_amount: Decimal | None
    # Human-readable status for the empty/partial cases (no DOB, pre-RMD age,
    # no pretax accounts, missing year-end balance).
    note: str | None


class RequiredDistributionsReport(BaseModel):
    year: int
    members: list[MemberRequiredDistribution]
