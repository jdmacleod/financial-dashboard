import { api } from "./client"
import type { PensionAccountCreate, PensionAccountResponse, PensionAccountUpdate } from "./types"

export const pensionApi = {
  get: (accountId: string) => api.get<PensionAccountResponse>(`/accounts/${accountId}/pension`),

  create: (accountId: string, data: PensionAccountCreate) =>
    api.post<PensionAccountResponse>(`/accounts/${accountId}/pension`, data),

  update: (accountId: string, data: PensionAccountUpdate) =>
    api.patch<PensionAccountResponse>(`/accounts/${accountId}/pension`, data),
}
