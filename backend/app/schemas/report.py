import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PensionAnnotation(BaseModel):
    account_id: uuid.UUID
    nickname: str
    monthly_benefit: Decimal | None
    eligibility_age: int | None
    eligibility_date: date | None


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


class CashFlowReport(BaseModel):
    series: list[CashFlowPeriod]
    totals: CashFlowTotals


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


class BudgetVsActualsReport(BaseModel):
    period: str
    categories: list[BudgetVsActualsItem]


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
