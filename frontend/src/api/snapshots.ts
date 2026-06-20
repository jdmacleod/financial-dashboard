import { api } from "./client"
import type { SnapshotResponse } from "./types"

export const snapshotsApi = {
  list: (accountId: string) => api.get<SnapshotResponse[]>(`/accounts/${accountId}/snapshots`),

  create: (accountId: string, data: { balance: string; snapshot_date: string }) =>
    api.post<SnapshotResponse>(`/accounts/${accountId}/snapshots`, data),
}
