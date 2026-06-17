import { api } from "./client"
import type { PaginatedAuditLog } from "./types"

export const auditLogApi = {
  list: (
    params: {
      entity_type?: string
      entity_id?: string
      user_id?: string
      member_id?: string
      from?: string
      to?: string
      page?: number
      page_size?: number
    } = {},
  ) => {
    const qs = new URLSearchParams()
    if (params.entity_type) qs.set("entity_type", params.entity_type)
    if (params.entity_id) qs.set("entity_id", params.entity_id)
    if (params.user_id) qs.set("user_id", params.user_id)
    if (params.member_id) qs.set("member_id", params.member_id)
    if (params.from) qs.set("from", params.from)
    if (params.to) qs.set("to", params.to)
    if (params.page) qs.set("page", String(params.page))
    if (params.page_size) qs.set("page_size", String(params.page_size))
    const suffix = qs.toString() ? `?${qs.toString()}` : ""
    return api.get<PaginatedAuditLog>(`/audit-log${suffix}`)
  },
}
