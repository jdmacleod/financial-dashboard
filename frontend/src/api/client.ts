const BASE = "/api/v1"

let _accessToken: string | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
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

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? data ?? res.statusText)
  }
  return data as T
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
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

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    throw new ApiError(res.status, data?.detail ?? data ?? res.statusText)
  }
  return data as T
}

export const apiUpload = {
  post: <T>(path: string, form: FormData) => requestForm<T>(path, form),
}
