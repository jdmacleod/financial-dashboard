import { api } from "./client"
import type { SnapshotResponse } from "./types"

export const snapshotsApi = {
  create: (accountId: string, data: { balance: string; snapshot_date: string }) =>
    api.post<SnapshotResponse>(`/accounts/${accountId}/snapshots`, data),
}
