import { QueryClient } from "@tanstack/react-query"

// Single app-wide QueryClient. Exported (not created inline in main.tsx) so the
// auth layer can clear it on logout: query keys are not user-scoped, and with a
// 30s staleTime a new login would otherwise render the previous user's cached
// data (e.g. the wrong household). See useAuth.logout / clearAuth.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})
