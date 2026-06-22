import { api } from "./client"
import type { EquityGrantResponse } from "./types"

export const equityGrantsApi = {
  list: (params?: { member_id?: string }) => {
    const suffix = params?.member_id ? `?member_id=${params.member_id}` : ""
    return api.get<EquityGrantResponse[]>(`/equity-grants${suffix}`)
  },
}
