import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { api, setAccessToken, ApiError } from "../client"

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch)
  vi.stubGlobal("sessionStorage", {
    getItem: vi.fn(),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  })
  // Capture location.href assignment without navigating
  Object.defineProperty(window, "location", {
    value: { href: "" },
    writable: true,
  })
  setAccessToken("expired-token")
})

afterEach(() => {
  vi.restoreAllMocks()
  mockFetch.mockReset()
  setAccessToken(null)
})

function jsonResponse(body: unknown, status = 200): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
    statusText: status === 200 ? "OK" : "Error",
  } as unknown as Response
}

describe("token refresh on 401", () => {
  it("retries request with new token after successful refresh", async () => {
    // First call: 401 (token expired)
    // Second call: refresh succeeds
    // Third call: original request retried with new token
    mockFetch
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({ access_token: "new-token" }, 200))
      .mockResolvedValueOnce(jsonResponse({ id: "account-1" }, 200))

    const result = await api.get<{ id: string }>("/accounts")

    expect(result).toEqual({ id: "account-1" })
    expect(mockFetch).toHaveBeenCalledTimes(3)

    // Second call must be the refresh endpoint
    const refreshCall = mockFetch.mock.calls[1]
    expect(refreshCall[0]).toBe("/api/v1/auth/refresh")
    expect(refreshCall[1]).toMatchObject({ method: "POST", credentials: "include" })

    // Third call must carry the new token
    const retryCall = mockFetch.mock.calls[2]
    expect(retryCall[1].headers["Authorization"]).toBe("Bearer new-token")

    // sessionStorage must be updated
    expect(sessionStorage.setItem).toHaveBeenCalledWith("access_token", "new-token")
  })

  it("redirects to /login when refresh token is expired", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({}, 401)) // original request
      .mockResolvedValueOnce(jsonResponse({}, 401)) // refresh also fails

    await expect(api.get("/accounts")).rejects.toThrow(ApiError)

    expect(window.location.href).toBe("/login")
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("access_token")
  })

  it("redirects to /login when retried request still returns 401", async () => {
    mockFetch
      .mockResolvedValueOnce(jsonResponse({}, 401)) // original
      .mockResolvedValueOnce(jsonResponse({ access_token: "new-token" }, 200)) // refresh ok
      .mockResolvedValueOnce(jsonResponse({}, 401)) // retry still 401

    await expect(api.get("/accounts")).rejects.toThrow(ApiError)

    expect(window.location.href).toBe("/login")
    expect(sessionStorage.removeItem).toHaveBeenCalledWith("access_token")
  })

  it("does NOT attempt refresh for /auth/* paths", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: "Invalid credentials" }, 401))

    await expect(api.post("/auth/login", { email: "x", password: "y" })).rejects.toMatchObject({
      status: 401,
    })

    // Only one fetch call — no refresh attempt
    expect(mockFetch).toHaveBeenCalledTimes(1)
    expect(window.location.href).not.toBe("/login")
  })

  it("deduplicates concurrent refresh calls", async () => {
    // Three parallel 401s — should trigger exactly one refresh
    mockFetch
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({}, 401))
      .mockResolvedValueOnce(jsonResponse({ access_token: "new-token" }, 200))
      .mockResolvedValueOnce(jsonResponse({ id: "a" }, 200))
      .mockResolvedValueOnce(jsonResponse({ id: "b" }, 200))
      .mockResolvedValueOnce(jsonResponse({ id: "c" }, 200))

    await Promise.all([api.get("/accounts"), api.get("/accounts"), api.get("/accounts")])

    const refreshCalls = mockFetch.mock.calls.filter((c) => c[0] === "/api/v1/auth/refresh")
    expect(refreshCalls).toHaveLength(1)
  })
})
