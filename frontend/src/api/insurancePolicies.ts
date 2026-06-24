import { api } from "./client"
import type { InsurancePolicyResponse } from "./types"

export interface InsurancePolicyCreate {
  policy_type: string
  insured_member_id: string | null
  owner_ownership_entity_id: string | null
  coverage_amount: string
  premium_amount: string
  premium_cadence: string
  cash_value_account_id: string | null
  carrier: string | null
  policy_number: string | null
  technical_notes: string | null
  insured_real_estate_id: string | null
  metadata: Record<string, unknown>
}

export interface InsurancePolicyUpdate {
  policy_type?: string
  coverage_amount?: string
  premium_amount?: string
  premium_cadence?: string
  carrier?: string | null
  policy_number?: string | null
  technical_notes?: string | null
  insured_real_estate_id?: string | null
}

export const insurancePoliciesApi = {
  list: () => api.get<InsurancePolicyResponse[]>("/insurance-policies"),
  create: (data: InsurancePolicyCreate) =>
    api.post<InsurancePolicyResponse>("/insurance-policies", data),
  update: (id: string, data: InsurancePolicyUpdate) =>
    api.patch<InsurancePolicyResponse>(`/insurance-policies/${id}`, data),
  delete: (id: string) => api.delete(`/insurance-policies/${id}`),
}
