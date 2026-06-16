import { create } from "zustand"
import { setAccessToken } from "@/api/client"
import { authApi } from "@/api/auth"

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  restoreToken: (token: string) => void
  clearAuth: () => void
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  restoreToken: (token: string) => {
    setAccessToken(token)
    set({ token, isAuthenticated: true })
  },

  login: async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setAccessToken(res.access_token)
    sessionStorage.setItem("access_token", res.access_token)
    set({ token: res.access_token, isAuthenticated: true })
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore errors on logout
    }
    setAccessToken(null)
    sessionStorage.removeItem("access_token")
    set({ token: null, isAuthenticated: false })
  },

  clearAuth: () => {
    setAccessToken(null)
    sessionStorage.removeItem("access_token")
    set({ token: null, isAuthenticated: false })
  },
}))
