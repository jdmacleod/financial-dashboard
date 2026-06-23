import { api } from "./client"
import type { InvestmentLotResponse, PositionsSummary } from "./types"

export const investmentLotsApi = {
  list: (params?: { account_id?: string }) => {
    const suffix = params?.account_id ? `?account_id=${params.account_id}` : ""
    return api.get<InvestmentLotResponse[]>(`/investment-lots${suffix}`)
  },
  positions: () => api.get<PositionsSummary>("/investment-positions"),
}
