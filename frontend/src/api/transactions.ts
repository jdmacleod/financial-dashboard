import { api } from "./client"
import type { PaginatedTransactions, TransactionCreate, TransactionResponse } from "./types"

export interface TransactionFilters {
  from?: string
  to?: string
  category_id?: string
  is_reviewed?: boolean
  is_transfer?: boolean
  real_estate_property_id?: string
  search?: string
  page?: number
  page_size?: number
}

function buildQuery(filters: TransactionFilters): string {
  const params = new URLSearchParams()
  if (filters.from) params.set("from", filters.from)
  if (filters.to) params.set("to", filters.to)
  if (filters.category_id) params.set("category_id", filters.category_id)
  if (filters.is_reviewed !== undefined) params.set("is_reviewed", String(filters.is_reviewed))
  if (filters.is_transfer !== undefined) params.set("is_transfer", String(filters.is_transfer))
  if (filters.real_estate_property_id) {
    params.set("real_estate_property_id", filters.real_estate_property_id)
  }
  if (filters.search) params.set("search", filters.search)
  if (filters.page) params.set("page", String(filters.page))
  if (filters.page_size) params.set("page_size", String(filters.page_size))
  const qs = params.toString()
  return qs ? `?${qs}` : ""
}

export const transactionsApi = {
  list: (accountId: string, filters: TransactionFilters = {}) =>
    api.get<PaginatedTransactions>(`/accounts/${accountId}/transactions${buildQuery(filters)}`),

  create: (accountId: string, data: TransactionCreate) =>
    api.post<TransactionResponse>(`/accounts/${accountId}/transactions`, data),

  update: (
    id: string,
    data: Partial<{
      transaction_date: string
      amount: string
      payee_normalized: string
      memo: string | null
      category_id: string | null
      is_transfer: boolean
      real_estate_property_id: string | null
      is_reviewed: boolean
    }>,
  ) => api.patch<TransactionResponse>(`/transactions/${id}`, data),

  delete: (id: string) => api.delete(`/transactions/${id}`),

  bulkCategorize: (accountId: string, transactionIds: string[], categoryId: string) =>
    api.patch<TransactionResponse[]>(`/accounts/${accountId}/transactions/bulk-categorize`, {
      transaction_ids: transactionIds,
      category_id: categoryId,
    }),
}
