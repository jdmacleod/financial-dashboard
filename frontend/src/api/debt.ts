import { api } from "./client"
import type { DebtPayoffComparisonResponse } from "./types"

export const debtApi = {
  payoffComparison: (extraMonthlyPayment?: number, strategy?: string) => {
    const params = new URLSearchParams()
    if (extraMonthlyPayment !== undefined && extraMonthlyPayment !== 0) {
      params.set("extra_monthly_payment", String(extraMonthlyPayment))
    }
    if (strategy) {
      params.set("strategy", strategy)
    }
    const qs = params.toString()
    return api.get<DebtPayoffComparisonResponse>(`/debt-payoff${qs ? `?${qs}` : ""}`)
  },
}
