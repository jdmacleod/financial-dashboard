import { api, apiUpload } from "./client"
import type { ImportJobResponse, ImportPreviewResponse } from "./types"

export const importsApi = {
  preview: (accountId: string, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return apiUpload.post<ImportPreviewResponse>(`/accounts/${accountId}/import/preview`, form)
  },

  start: (accountId: string, file: File, mapping?: Record<string, string>) => {
    const form = new FormData()
    form.append("file", file)
    if (mapping) form.append("mapping", JSON.stringify(mapping))
    return apiUpload.post<ImportJobResponse>(`/accounts/${accountId}/import`, form)
  },

  getJob: (jobId: string) => api.get<ImportJobResponse>(`/import-jobs/${jobId}`),

  listJobs: () => api.get<ImportJobResponse[]>("/import-jobs"),
}
