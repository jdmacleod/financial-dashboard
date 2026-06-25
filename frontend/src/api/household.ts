import { api } from "./client"
import type { HouseholdResponse, HouseholdUpdate } from "./types"

export const householdApi = {
  get: () => api.get<HouseholdResponse>("/household"),
  update: (data: HouseholdUpdate) => api.patch<HouseholdResponse>("/household", data),
}
