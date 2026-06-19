import { api } from "./client"
import type { HouseholdResponse } from "./types"

export const householdApi = {
  get: () => api.get<HouseholdResponse>("/household"),
}
