import { api } from "./client"
import type { ProvisionResponse, TemporaryPasswordResponse } from "./types"

export const provisioningApi = {
  /** Add a login-capable member in one action; returns the temp password once. */
  provision: (data: {
    display_name: string
    role: "primary" | "partner" | "dependent"
    email: string
    date_of_birth?: string | null
  }) => api.post<ProvisionResponse>("/members/provision", data),

  /** Re-issue a temporary password for a not-yet-claimed provisioned user. */
  regenerateTemporaryPassword: (userId: string) =>
    api.post<TemporaryPasswordResponse>(`/members/users/${userId}/temporary-password`),
}
