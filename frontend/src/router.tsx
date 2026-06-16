import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from "@tanstack/react-router"
import { authApi } from "@/api/auth"
import { setAccessToken } from "@/api/client"
import Login from "@/pages/Login"
import Setup from "@/pages/Setup"
import Members from "@/pages/Members"
import Accounts from "@/pages/Accounts"

// Root layout — checks auth + setup state
const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

// Public routes
const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: Login,
})

const setupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/setup",
  component: Setup,
})

// Protected layout — redirects to /login if no token, /setup if not configured
const appLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  beforeLoad: async () => {
    const stored = sessionStorage.getItem("access_token")
    if (!stored) {
      try {
        const res = await authApi.setupStatus()
        if (!res.setup_complete) throw redirect({ to: "/setup" })
      } catch (e: unknown) {
        if (e && typeof e === "object" && "to" in e) throw e
      }
      throw redirect({ to: "/login" })
    }
    setAccessToken(stored)
  },
  component: AppLayout,
})

function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
          <span className="font-semibold text-gray-900">HearthLedger</span>
          <a href="/" className="text-sm text-gray-600 hover:text-gray-900">Dashboard</a>
          <a href="/accounts" className="text-sm text-gray-600 hover:text-gray-900">Accounts</a>
          <a href="/members" className="text-sm text-gray-600 hover:text-gray-900">Members</a>
        </div>
      </nav>
      <Outlet />
    </div>
  )
}

const indexRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/",
  component: () => (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-semibold mb-2">Dashboard</h1>
      <p className="text-gray-500">Dashboard will be built in Phase 3.</p>
    </div>
  ),
})

const membersRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/members",
  component: Members,
})

const accountsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/accounts",
  component: Accounts,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  setupRoute,
  appLayoutRoute.addChildren([indexRoute, membersRoute, accountsRoute]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
