import { api } from "./client"
import type { InsurancePolicyResponse } from "./types"

export const insurancePoliciesApi = {
  list: () => api.get<InsurancePolicyResponse[]>("/insurance-policies"),
}
