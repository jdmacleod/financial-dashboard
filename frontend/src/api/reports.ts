import { api } from "./client"
import type {
  AgeMilestonesReport,
  BudgetTrendReport,
  BudgetVsActualsReport,
  CashFlowReport,
  DashboardResponse,
  EstateExposureReport,
  NetWorthReport,
  PropertyPnLReport,
  RequiredDistributionsReport,
  SavingsRateReport,
  SpendingByCategoryReport,
} from "./types"

export const reportsApi = {
  netWorth: (from: string, to: string, interval: "monthly" | "quarterly" | "annual" = "monthly") =>
    api.get<NetWorthReport>(`/reports/net-worth?from=${from}&to=${to}&interval=${interval}`),

  cashFlow: (from: string, to: string, groupBy: "month" | "quarter" = "month") =>
    api.get<CashFlowReport>(`/reports/cash-flow?from=${from}&to=${to}&group_by=${groupBy}`),

  spendingByCategory: (from: string, to: string, parentCategoryId?: string) => {
    const qs = new URLSearchParams({ from, to })
    if (parentCategoryId) qs.set("parent_category_id", parentCategoryId)
    return api.get<SpendingByCategoryReport>(`/reports/spending-by-category?${qs.toString()}`)
  },

  budgetVsActuals: (month: string) =>
    api.get<BudgetVsActualsReport>(`/reports/budget-vs-actuals?month=${month}`),

  budgetTrend: (from: string, to: string) =>
    api.get<BudgetTrendReport>(`/reports/budget-trend?from=${from}&to=${to}`),

  savingsRate: (from: string, to: string) =>
    api.get<SavingsRateReport>(`/reports/savings-rate?from=${from}&to=${to}`),

  requiredDistributions: (year?: number) =>
    api.get<RequiredDistributionsReport>(
      `/reports/required-distributions${year ? `?year=${year}` : ""}`,
    ),

  ageMilestones: () => api.get<AgeMilestonesReport>("/reports/age-milestones"),

  propertyPnl: (propertyId: string, from: string, to: string) =>
    api.get<PropertyPnLReport>(
      `/reports/property-pnl?property_id=${propertyId}&from=${from}&to=${to}`,
    ),

  estateExposure: (asOf?: string) =>
    api.get<EstateExposureReport>(`/reports/estate-exposure${asOf ? `?as_of=${asOf}` : ""}`),

  dashboard: () => api.get<DashboardResponse>("/dashboard"),
}
