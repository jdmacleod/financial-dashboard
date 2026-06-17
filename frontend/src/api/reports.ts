import { api } from "./client"
import type {
  BudgetVsActualsReport,
  CashFlowReport,
  DashboardResponse,
  NetWorthReport,
  PropertyPnLReport,
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

  propertyPnl: (propertyId: string, from: string, to: string) =>
    api.get<PropertyPnLReport>(
      `/reports/property-pnl?property_id=${propertyId}&from=${from}&to=${to}`,
    ),

  dashboard: () => api.get<DashboardResponse>("/dashboard"),
}
