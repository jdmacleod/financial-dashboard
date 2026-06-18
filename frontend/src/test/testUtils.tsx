import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { CategoryResponse } from "@/api/types"

export function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

export function wrapper(client: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

export const contributionsCategory: CategoryResponse = {
  id: "cat-contributions",
  household_id: "hh1",
  name: "Contributions",
  parent_category_id: null,
  color_hex: "#4f46e5",
  icon: null,
  is_income: false,
  is_system: true,
  created_at: "2025-01-01T00:00:00Z",
}

export const incomeCategory: CategoryResponse = {
  id: "cat-income",
  household_id: "hh1",
  name: "Income",
  parent_category_id: null,
  color_hex: "#10b981",
  icon: null,
  is_income: true,
  is_system: true,
  created_at: "2025-01-01T00:00:00Z",
}
