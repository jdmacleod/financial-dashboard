import { api } from "./client"
import type { AdvisoryNoteResponse } from "./types"

export const advisoryNotesApi = {
  list: (params?: { account_id?: string; ownership_entity_id?: string; category?: string }) => {
    const qs = new URLSearchParams()
    if (params?.account_id) qs.set("account_id", params.account_id)
    if (params?.ownership_entity_id) qs.set("ownership_entity_id", params.ownership_entity_id)
    if (params?.category) qs.set("category", params.category)
    const suffix = qs.toString() ? `?${qs.toString()}` : ""
    return api.get<AdvisoryNoteResponse[]>(`/advisory-notes${suffix}`)
  },
}
