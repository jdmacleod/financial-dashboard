import { create } from "zustand"
import { setAccessToken } from "@/api/client"
import { authApi } from "@/api/auth"
import { queryClient } from "@/lib/queryClient"

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
  // True when the user signed in with a provisioned temporary password and must
  // set their own before reaching the app. Persisted so a refresh mid-reset
  // still gates. Cleared by clearMustChangePassword after a successful reset.
  mustChangePassword: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  restoreToken: (token: string) => void
  clearAuth: () => void
  clearMustChangePassword: () => void
}

const MCP_KEY = "must_change_password"

export const useAuth = create<AuthState>((set) => ({
  token: null,
  isAuthenticated: false,
  role: null,
  memberId: null,
  mustChangePassword: sessionStorage.getItem(MCP_KEY) === "true",

  restoreToken: (token: string) => {
    setAccessToken(token)
    const payload = decodeJwtPayload(token)
    set({
      token,
      isAuthenticated: true,
      role: payload?.role ?? null,
      memberId: payload?.member_id ?? null,
      mustChangePassword: sessionStorage.getItem(MCP_KEY) === "true",
    })
  },

  login: async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    setAccessToken(res.access_token)
    sessionStorage.setItem("access_token", res.access_token)
    const mustChange = res.must_change_password === true
    if (mustChange) sessionStorage.setItem(MCP_KEY, "true")
    else sessionStorage.removeItem(MCP_KEY)
    const payload = decodeJwtPayload(res.access_token)
    set({
      token: res.access_token,
      isAuthenticated: true,
      role: payload?.role ?? null,
      memberId: payload?.member_id ?? null,
      mustChangePassword: mustChange,
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
    sessionStorage.removeItem(MCP_KEY)
    // Wipe the React Query cache. Query keys aren't user-scoped, so without this
    // the next login renders the previous user's cached data (e.g. the wrong
    // household) until each query's staleTime elapses.
    queryClient.clear()
    set({
      token: null,
      isAuthenticated: false,
      role: null,
      memberId: null,
      mustChangePassword: false,
    })
  },

  clearAuth: () => {
    setAccessToken(null)
    sessionStorage.removeItem("access_token")
    sessionStorage.removeItem(MCP_KEY)
    queryClient.clear()
    set({
      token: null,
      isAuthenticated: false,
      role: null,
      memberId: null,
      mustChangePassword: false,
    })
  },

  clearMustChangePassword: () => {
    sessionStorage.removeItem(MCP_KEY)
    set({ mustChangePassword: false })
  },
}))
