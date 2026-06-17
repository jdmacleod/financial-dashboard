import { api } from "./client"
import type { BackupJobResponse } from "./types"

export const backupsApi = {
  list: () => api.get<BackupJobResponse[]>("/backups"),
  trigger: () => api.post<BackupJobResponse>("/backups", {}),
  downloadUrl: (jobId: string) => `/api/v1/backups/${jobId}/download`,
}
