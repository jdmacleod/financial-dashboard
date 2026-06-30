import { describe, it, expect, beforeEach } from "vitest"
import { queryClient } from "../queryClient"
import { syncSessionCache, __resetSessionCacheForTests } from "../sessionCache"

// Builds a minimal unsigned JWT carrying just the `sub` claim, which is all the
// identity-transition guard reads.
function tokenFor(sub: string): string {
  const payload = btoa(JSON.stringify({ sub }))
  return `header.${payload}.sig`
}

describe("sessionCache — identity-transition guard", () => {
  beforeEach(() => {
    queryClient.clear()
    __resetSessionCacheForTests()
  })

  it("clears the cache when the token swaps to a DIFFERENT user", () => {
    // User A is signed in with cached data, then the token swaps to user B
    // WITHOUT going through logout (the gap this guard closes).
    syncSessionCache(tokenFor("user-a"))
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    syncSessionCache(tokenFor("user-b"))

    expect(queryClient.getQueryData(["accounts"])).toBeUndefined()
  })

  it("does NOT clear on a same-user token refresh", () => {
    // A silent refresh issues a new token string for the same identity; the
    // cache must survive so refreshes don't thrash it.
    syncSessionCache(tokenFor("user-a"))
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    syncSessionCache(tokenFor("user-a"))

    expect(queryClient.getQueryData(["accounts"])).toEqual([{ id: "a1" }])
  })

  it("does NOT clear when logging in from a clean (no-user) state", () => {
    // Nothing is cached to leak into, and login already follows a logout that
    // cleared the cache — so the first sign-in must not wipe freshly-set data.
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    syncSessionCache(tokenFor("user-a"))

    expect(queryClient.getQueryData(["accounts"])).toEqual([{ id: "a1" }])
  })

  it("clears on logout (user -> no token), backstopping the explicit clear", () => {
    syncSessionCache(tokenFor("user-a"))
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    syncSessionCache(null)

    expect(queryClient.getQueryData(["accounts"])).toBeUndefined()
  })

  it("treats a malformed token as no identity and does not throw", () => {
    syncSessionCache(tokenFor("user-a"))
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    // A garbage token decodes to no subject (user -> none): treated like logout.
    expect(() => syncSessionCache("not-a-jwt")).not.toThrow()
    expect(queryClient.getQueryData(["accounts"])).toBeUndefined()
  })

  it("treats a token with a non-string sub claim as no identity", () => {
    // A well-formed JWT whose `sub` is missing/numeric carries no usable
    // identity, so it is treated as "no user" (user -> none clears, like logout).
    const numericSub = `header.${btoa(JSON.stringify({ sub: 123 }))}.sig`
    syncSessionCache(tokenFor("user-a"))
    queryClient.setQueryData(["accounts"], [{ id: "a1" }])

    syncSessionCache(numericSub)

    expect(queryClient.getQueryData(["accounts"])).toBeUndefined()
  })
})
