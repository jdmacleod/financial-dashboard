import { api } from "./client"
import type { AccessGrantResponse, AccountResponse, AccountType } from "./types"

export const accountsApi = {
  list: () => api.get<AccountResponse[]>("/accounts"),

  get: (id: string) => api.get<AccountResponse>(`/accounts/${id}`),

  create: (data: {
    account_type: AccountType
    nickname: string
    owner_member_id?: string | null
    institution_name?: string | null
    account_number?: string | null
    routing_number?: string | null
    include_in_net_worth?: boolean
    notes?: string | null
  }) => api.post<AccountResponse>("/accounts", data),

  update: (
    id: string,
    data: Partial<{
      nickname: string
      owner_member_id: string | null
      ownership_entity_id: string | null
      institution_name: string | null
      account_number: string | null
      routing_number: string | null
      include_in_net_worth: boolean
      notes: string | null
    }>,
  ) => api.patch<AccountResponse>(`/accounts/${id}`, data),

  deactivate: (id: string) => api.delete(`/accounts/${id}`),

  listGrants: (accountId: string) =>
    api.get<AccessGrantResponse[]>(`/accounts/${accountId}/grants`),

  createGrant: (accountId: string, grantee_member_id: string) =>
    api.post<AccessGrantResponse>(`/accounts/${accountId}/grants`, { grantee_member_id }),

  revokeGrant: (accountId: string, grantId: string) =>
    api.delete(`/accounts/${accountId}/grants/${grantId}`),
}
