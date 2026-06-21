import { api } from "./client"
import type {
  FireDetectionResponse,
  FireProjectionResponse,
  FireScenarioResponse,
  IncomeStream,
} from "./types"

export const fireApi = {
  list: () => api.get<FireScenarioResponse[]>("/fire-scenarios"),

  get: (id: string) => api.get<FireScenarioResponse>(`/fire-scenarios/${id}`),

  create: (data: {
    name: string
    target_annual_spend: string
    safe_withdrawal_rate?: string
    expected_annual_return?: string
    expected_inflation_rate?: string
    target_retirement_age?: number | null
    member_id?: string | null
    additional_income_streams?: IncomeStream[]
  }) => api.post<FireScenarioResponse>("/fire-scenarios", data),

  update: (
    id: string,
    data: Partial<{
      name: string
      target_annual_spend: string
      safe_withdrawal_rate: string
      expected_annual_return: string
      expected_inflation_rate: string
      target_retirement_age: number | null
      member_id: string | null
      additional_income_streams: IncomeStream[]
      detection_trailing_months: number
    }>,
  ) => api.patch<FireScenarioResponse>(`/fire-scenarios/${id}`, data),

  delete: (id: string) => api.delete(`/fire-scenarios/${id}`),

  detect: (id: string, trailing_months?: number) =>
    api.post<FireDetectionResponse>(
      `/fire-scenarios/${id}/detect${trailing_months !== undefined ? `?trailing_months=${trailing_months}` : ""}`,
    ),

  projection: (id: string, from_year?: number) =>
    api.get<FireProjectionResponse>(
      `/fire-scenarios/${id}/projection${from_year !== undefined ? `?from_year=${from_year}` : ""}`,
    ),
}
