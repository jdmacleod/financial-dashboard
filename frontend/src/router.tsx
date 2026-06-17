import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from "@tanstack/react-router"
import { authApi } from "@/api/auth"
import { useAuth } from "@/hooks/useAuth"
import { AppLayout } from "@/components/app/AppLayout"
import Login from "@/pages/Login"
import Setup from "@/pages/Setup"
import Members from "@/pages/Members"
import Accounts from "@/pages/Accounts"
import Transactions from "@/pages/Transactions"
import Categories from "@/pages/Categories"

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
    useAuth.getState().restoreToken(stored)
  },
  component: AppLayout,
})

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

const accountTransactionsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/accounts/$accountId/transactions",
  component: Transactions,
})

const categoriesRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/categories",
  component: Categories,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  setupRoute,
  appLayoutRoute.addChildren([
    indexRoute,
    membersRoute,
    accountsRoute,
    accountTransactionsRoute,
    categoriesRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
