import { describe, it, expect, vi, beforeEach } from "vitest"
import { useAuth } from "../useAuth"
import { queryClient } from "@/lib/queryClient"

vi.mock("@/api/auth", () => ({
  authApi: {
    login: vi.fn(async () => ({
      access_token: "header.eyJzdWIiOiJ4In0.sig",
      must_change_password: false,
    })),
    logout: vi.fn(async () => {}),
  },
}))

vi.mock("@/api/client", () => ({
  setAccessToken: vi.fn(),
}))

describe("useAuth — query cache isolation across accounts", () => {
  beforeEach(() => {
    queryClient.clear()
    useAuth.setState({ token: null, isAuthenticated: false, role: null, memberId: null })
  })

  it("clears the React Query cache on logout so the next user can't see cached data", async () => {
    // Simulate the previous user's cached household data.
    queryClient.setQueryData(["household"], { name: "Langford Household" })
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])
    expect(queryClient.getQueryData(["household"])).toBeDefined()

    await useAuth.getState().logout()

    // The bug: without queryClient.clear() in logout, this data would survive
    // and the next login would render the previous household.
    expect(queryClient.getQueryData(["household"])).toBeUndefined()
    expect(queryClient.getQueryData(["accounts"])).toBeUndefined()
    expect(useAuth.getState().isAuthenticated).toBe(false)
  })

  it("clears the React Query cache on clearAuth (forced teardown)", () => {
    queryClient.setQueryData(["household"], { name: "Langford Household" })

    useAuth.getState().clearAuth()

    expect(queryClient.getQueryData(["household"])).toBeUndefined()
  })
})
