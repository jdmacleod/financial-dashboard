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
import Dashboard from "@/pages/Dashboard"
import ReportNetWorth from "@/pages/ReportNetWorth"
import ReportCashFlow from "@/pages/ReportCashFlow"
import ReportSpending from "@/pages/ReportSpending"
import Budgets from "@/pages/Budgets"
import PropertyDetail from "@/pages/PropertyDetail"
import SettingsActivity from "@/pages/SettingsActivity"
import SettingsSecurity from "@/pages/SettingsSecurity"

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
  component: Dashboard,
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

const reportsNetWorthRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/reports/net-worth",
  component: ReportNetWorth,
})

const reportsCashFlowRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/reports/cash-flow",
  component: ReportCashFlow,
})

const reportsSpendingRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/reports/spending",
  component: ReportSpending,
})

const budgetsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/budgets",
  component: Budgets,
})

const propertyDetailRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/properties/$propertyId",
  component: PropertyDetail,
})

const settingsActivityRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/activity",
  component: SettingsActivity,
})

const settingsSecurityRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/security",
  component: SettingsSecurity,
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
    reportsNetWorthRoute,
    reportsCashFlowRoute,
    reportsSpendingRoute,
    budgetsRoute,
    propertyDetailRoute,
    settingsActivityRoute,
    settingsSecurityRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
