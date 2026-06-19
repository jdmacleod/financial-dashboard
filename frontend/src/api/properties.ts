import { api } from "./client"
import type {
  PropertyEquityResponse,
  PropertyResponse,
  PropertyType,
  ValuationResponse,
  ValuationSource,
} from "./types"

export const propertiesApi = {
  get: (id: string) => api.get<PropertyResponse>(`/properties/${id}`),

  getByAccountId: (accountId: string) =>
    api.get<PropertyResponse>(`/accounts/${accountId}/property`),

  create: (data: {
    account_id: string
    address: string
    purchase_date?: string | null
    purchase_price?: string | null
    linked_mortgage_account_id?: string | null
    property_type?: PropertyType
  }) => api.post<PropertyResponse>("/properties", data),

  update: (
    id: string,
    data: Partial<{
      address: string
      purchase_date: string | null
      purchase_price: string | null
      linked_mortgage_account_id: string | null
      property_type: PropertyType
    }>,
  ) => api.patch<PropertyResponse>(`/properties/${id}`, data),

  getEquity: (id: string) => api.get<PropertyEquityResponse>(`/properties/${id}/equity`),

  listValuations: (id: string) => api.get<ValuationResponse[]>(`/properties/${id}/valuations`),

  addValuation: (
    id: string,
    data: { valuation_date: string; estimated_value: string; source?: ValuationSource },
  ) => api.post<ValuationResponse>(`/properties/${id}/valuations`, data),
}
