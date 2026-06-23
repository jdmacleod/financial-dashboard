import { api } from "./client"
import type { OwnershipEntityResponse } from "./types"

export interface OwnershipEntityCreate {
  entity_type: string
  name: string
  grantor_member_id: string | null
  is_in_taxable_estate: boolean
  counts_in_personal_net_worth: boolean
}

export interface OwnershipEntityUpdate {
  entity_type?: string
  name?: string
  grantor_member_id?: string | null
  is_in_taxable_estate?: boolean
  counts_in_personal_net_worth?: boolean
}

export const ownershipEntitiesApi = {
  list: () => api.get<OwnershipEntityResponse[]>("/ownership-entities"),
  create: (data: OwnershipEntityCreate) =>
    api.post<OwnershipEntityResponse>("/ownership-entities", data),
  update: (id: string, data: OwnershipEntityUpdate) =>
    api.patch<OwnershipEntityResponse>(`/ownership-entities/${id}`, data),
  delete: (id: string) => api.delete(`/ownership-entities/${id}`),
}
