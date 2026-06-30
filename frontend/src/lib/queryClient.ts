import { QueryClient } from "@tanstack/react-query"

// Single app-wide QueryClient. Exported (not created inline in main.tsx) so the
// auth layer can clear it: query keys are not user-scoped, and with a 30s
// staleTime a new login would otherwise render the previous user's cached data
// (e.g. the wrong household). It is cleared both explicitly on logout
// (useAuth.logout / clearAuth) and automatically whenever the access token swaps
// to a different identity (lib/sessionCache, hooked into setAccessToken), so a
// token swap that doesn't route through logout still can't leak cached data.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})
