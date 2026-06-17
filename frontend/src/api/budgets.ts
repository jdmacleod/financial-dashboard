import { api } from "./client"
import type { BudgetPeriod, BudgetResponse } from "./types"

export const budgetsApi = {
  list: (params: { category_id?: string; effective_date?: string } = {}) => {
    const qs = new URLSearchParams()
    if (params.category_id) qs.set("category_id", params.category_id)
    if (params.effective_date) qs.set("effective_date", params.effective_date)
    const suffix = qs.toString() ? `?${qs.toString()}` : ""
    return api.get<BudgetResponse[]>(`/budgets${suffix}`)
  },

  create: (data: {
    category_id: string
    period?: BudgetPeriod
    amount: string
    effective_from: string
    effective_to?: string | null
  }) => api.post<BudgetResponse>("/budgets", data),

  update: (
    id: string,
    data: Partial<{ amount: string; effective_from: string; effective_to: string | null }>,
  ) => api.patch<BudgetResponse>(`/budgets/${id}`, data),

  delete: (id: string) => api.delete(`/budgets/${id}`),
}
