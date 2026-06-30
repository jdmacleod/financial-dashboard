import { queryClient } from "./queryClient"

// Extracts the `sub` (user id) claim from a JWT without verifying it. Used only
// to detect identity transitions, never for authorization — the server re-checks
// every privileged request regardless. Returns null for a missing or malformed
// token (treated as "no identity").
function subjectOf(token: string | null): string | null {
  if (!token) return null
  try {
    const segment = token.split(".")[1]
    const json = atob(segment.replace(/-/g, "+").replace(/_/g, "/"))
    const payload = JSON.parse(json) as { sub?: unknown }
    return typeof payload.sub === "string" ? payload.sub : null
  } catch {
    return null
  }
}

let currentSubject: string | null = null

// Clears the React Query cache whenever the authenticated identity changes to a
// DIFFERENT user, so one account never renders another's cached data — no matter
// which code path swapped the token. Query keys aren't user-scoped, so a token
// swap that doesn't route through logout (e.g. a future "switch account without
// signing out" flow) would otherwise leave the previous user's cached responses
// in place until each query's staleTime elapsed. Hooking this into setAccessToken
// — the single chokepoint every token assignment passes through — makes the guard
// independent of the auth store and of remembering to clear in each new flow.
//
// Two transitions are intentionally NOT treated as a leak and do not clear:
//   - same subject (a silent token refresh) — so routine refreshes don't thrash
//     the cache; and
//   - "no user" -> a user (login on a fresh boot) — there is nothing cached to
//     leak into, and login already follows an explicit logout that cleared it.
// A user -> "no user" transition (logout) does clear, so this also backstops the
// explicit clear in useAuth.logout / clearAuth.
export function syncSessionCache(token: string | null): void {
  const nextSubject = subjectOf(token)
  if (currentSubject !== null && nextSubject !== currentSubject) {
    queryClient.clear()
  }
  currentSubject = nextSubject
}

// Test seam: reset the tracked identity so each test starts from "no user".
export function __resetSessionCacheForTests(): void {
  currentSubject = null
}
