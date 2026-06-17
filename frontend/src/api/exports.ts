import { api, getAccessToken } from "./client"
import type { ExportCreateResponse, ExportJobResponse, ExportType } from "./types"

export interface ExportCreateRequest {
  export_type: ExportType
  from_date: string
  to_date: string
  account_ids?: string[]
  include_transactions?: boolean
}

export const exportApi = {
  create: (data: ExportCreateRequest, reauthToken?: string) =>
    api.post<ExportCreateResponse>(
      "/exports",
      data,
      reauthToken ? { "X-Reauth-Token": reauthToken } : undefined,
    ),

  get: (id: string) => api.get<ExportJobResponse>(`/exports/${id}`),

  list: () => api.get<ExportJobResponse[]>("/exports"),

  downloadUrl: (id: string) => `/api/v1/exports/${id}/download`,

  download: async (id: string, reauthToken?: string): Promise<Blob> => {
    const headers: Record<string, string> = {}
    const token = getAccessToken()
    if (token) {
      headers["Authorization"] = `Bearer ${token}`
    }
    if (reauthToken) {
      headers["X-Reauth-Token"] = reauthToken
    }
    const res = await fetch(`/api/v1/exports/${id}/download`, {
      headers,
      credentials: "include",
    })
    if (!res.ok) {
      const data = await res.json().catch(() => null)
      throw new Error(data?.detail ?? `Download failed: ${res.status}`)
    }
    return res.blob()
  },
}
