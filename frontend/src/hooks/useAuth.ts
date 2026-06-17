import { create } from "zustand"
import { setAccessToken } from "@/api/client"
import { authApi } from "@/api/auth"

type Role = "primary" | "partner" | "dependent"

interface JwtPayload {
  sub: string
  member_id: string | null
  role: Role
}

// Decoded client-side for UI gating only (show/hide buttons) — the access
// token isn't verified here. Every privileged action is re-checked
// server-side regardless, per AccountService/MemberService.
function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const payload = token.split(".")[1]
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    return JSON.parse(json) as JwtPayload
  } catch {
    return null
  }
}

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  role: Role | null
  memberId: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  restoreToken: (token: string) => void
  clearAuth: () => void
}

export const useAuth = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  role: null,
  memberId: null,

  restoreToken: (token: string) => {
    setAccessToken(token)
    const payload = decodeJwtPayload(token)
    set({
      token,
      isAuthenticated: true,
      role: payload?.role ?? null,
      memberId: payload?.member_id ?? null,
    })
  },

  login: async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setAccessToken(res.access_token)
    sessionStorage.setItem("access_token", res.access_token)
    const payload = decodeJwtPayload(res.access_token)
    set({
      token: res.access_token,
      isAuthenticated: true,
      role: payload?.role ?? null,
      memberId: payload?.member_id ?? null,
    })
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {
      // ignore errors on logout
    }
    setAccessToken(null)
    sessionStorage.removeItem("access_token")
    set({ token: null, isAuthenticated: false, role: null, memberId: null })
  },

  clearAuth: () => {
    setAccessToken(null)
    sessionStorage.removeItem("access_token")
    set({ token: null, isAuthenticated: false, role: null, memberId: null })
  },
}))
