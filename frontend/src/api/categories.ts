import { api } from "./client"
import type { CategoryResponse } from "./types"

export const categoriesApi = {
  list: () => api.get<CategoryResponse[]>("/categories"),

  create: (data: {
    name: string
    parent_category_id?: string | null
    color_hex?: string
    icon?: string | null
    is_income?: boolean
  }) => api.post<CategoryResponse>("/categories", data),

  update: (
    id: string,
    data: Partial<{
      name: string
      parent_category_id: string | null
      color_hex: string
      icon: string | null
    }>,
  ) => api.patch<CategoryResponse>(`/categories/${id}`, data),

  delete: (id: string) => api.delete(`/categories/${id}`),
}
