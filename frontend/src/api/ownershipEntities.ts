import { api } from "./client"
import type { OwnershipEntityResponse } from "./types"

export const ownershipEntitiesApi = {
  list: () => api.get<OwnershipEntityResponse[]>("/ownership-entities"),
}
