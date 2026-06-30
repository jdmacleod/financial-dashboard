import { syncSessionCache } from "@/lib/sessionCache"

const BASE = "/api/v1"

let _accessToken: string | null = null
let _refreshPromise: Promise<string> | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
  // Drop the previous user's cached query data when the token swaps to a
  // different identity (see sessionCache). Silent refresh and expireSession set
  // _accessToken directly and bypass this — both are intentional: a refresh
  // keeps the same identity, and expireSession triggers a full-page redirect to
  // /login that discards the in-memory cache anyway.
  syncSessionCache(token)
}

export function getAccessToken(): string | null {
  return _accessToken
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail))
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

// Calls POST /auth/refresh directly (not via request()) to avoid recursion.
// Deduplicates concurrent refresh attempts so only one network call is made.
async function refreshAccessToken(): Promise<string> {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  })
    .then(async (res) => {
      if (!res.ok) throw new ApiError(401, "refresh_failed")
      const data = (await res.json()) as { access_token: string }
      _accessToken = data.access_token
      sessionStorage.setItem("access_token", data.access_token)
      return data.access_token
    })
    .finally(() => {
      _refreshPromise = null
    })
  return _refreshPromise
}

function expireSession(): never {
  _accessToken = null
  sessionStorage.removeItem("access_token")
  window.location.href = "/login"
  // Unreachable — satisfies TypeScript never return type
  throw new ApiError(401, "Session expired")
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extraHeaders,
  }
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 204) return undefined as T

  // Silent token refresh on 401. Skip for /auth/* paths: login wrong-password,
  // logout, and reauth failures are expected 401s that must not trigger a cycle.
  if (res.status === 401 && !path.startsWith("/auth/")) {
    let newToken: string
    try {
      newToken = await refreshAccessToken()
    } catch {
      expireSession()
    }
    const retryHeaders: Record<string, string> = {
      ...headers,
      Authorization: `Bearer ${newToken!}`,
    }
    const retry = await fetch(`${BASE}${path}`, {
      method,
      headers: retryHeaders,
      credentials: "include",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    if (retry.status === 204) return undefined as T
    if (retry.status === 401) expireSession()
    const retryData = await retry.json().catch(() => null)
    if (!retry.ok) {
      throw new ApiError(retry.status, retryData?.detail ?? retryData ?? retry.statusText)
    }
    return retryData as T
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? data ?? res.statusText)
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown, extraHeaders?: Record<string, string>) =>
    request<T>("POST", path, body, extraHeaders),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T = void>(path: string) => request<T>("DELETE", path),
}

// No Content-Type header here — the browser sets the multipart boundary
// itself when the body is a FormData instance.
async function requestForm<T>(path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`
  }

  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: form,
  })

  if (res.status === 401) {
    let newToken: string
    try {
      newToken = await refreshAccessToken()
    } catch {
      expireSession()
    }
    const retryHeaders: Record<string, string> = { Authorization: `Bearer ${newToken!}` }
    const retry = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: retryHeaders,
      credentials: "include",
      body: form,
    })
    if (retry.status === 401) expireSession()
    const retryData = await retry.json().catch(() => null)
    if (!retry.ok) {
      throw new ApiError(retry.status, retryData?.detail ?? retryData ?? retry.statusText)
    }
    return retryData as T
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? data ?? res.statusText)
  }
  return data as T
}

export const apiUpload = {
  post: <T>(path: string, form: FormData) => requestForm<T>(path, form),
}
