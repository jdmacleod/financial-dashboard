import { api } from "./client"
import type { TokenResponse } from "./types"

export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { email, password }),

  refresh: () => api.post<TokenResponse>("/auth/refresh"),

  logout: () => api.post<void>("/auth/logout"),

  reauth: (password: string) =>
    api.post<{ reauth_token: string }>("/auth/reauth", { password }),

  changePassword: (current_password: string, new_password: string) =>
    api.post<void>("/auth/change-password", { current_password, new_password }),

  setup: (data: {
    household_name: string
    member_name: string
    email: string
    password: string
  }) => api.post<TokenResponse>("/setup", data),

  setupStatus: () => api.get<{ setup_complete: boolean }>("/setup/status"),
}
