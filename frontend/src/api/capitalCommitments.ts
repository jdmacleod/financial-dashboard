import { api } from "./client"
import type { CapitalCommitmentResponse } from "./types"

export const capitalCommitmentsApi = {
  list: () => api.get<CapitalCommitmentResponse[]>("/capital-commitments"),
}
