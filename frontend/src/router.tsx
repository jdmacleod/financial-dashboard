import {
  createRootRoute,
  createRoute,
  createRouter,
  isRedirect,
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
import PensionDetail from "@/pages/PensionDetail"
import SettingsActivity from "@/pages/SettingsActivity"
import SettingsSecurity from "@/pages/SettingsSecurity"
import Fire from "@/pages/Fire"
import FireDetail from "@/pages/FireDetail"
import Debt from "@/pages/Debt"
import ExportsHistory from "@/pages/ExportsHistory"
import SettingsBackups from "@/pages/SettingsBackups"
import SettingsImports from "@/pages/SettingsImports"
import SettingsDashboard from "@/pages/SettingsDashboard"
import SettingsAppearance from "@/pages/SettingsAppearance"
import Assets from "@/pages/Assets"
import Investments from "@/pages/Investments"
import Retirement from "@/pages/Retirement"

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

type Range = "ytd" | "1y" | "all"
const VALID_RANGES: Range[] = ["ytd", "1y", "all"]

// Protected layout — redirects to /login if no token, /setup if not configured
const appLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  validateSearch: (search: Record<string, unknown>): { range?: Range } => {
    const raw = search.range as string | undefined
    return raw && VALID_RANGES.includes(raw as Range) ? { range: raw as Range } : {}
  },
  beforeLoad: async () => {
    const stored = sessionStorage.getItem("access_token")
    if (!stored) {
      try {
        const res = await authApi.setupStatus()
        if (!res.setup_complete) throw redirect({ to: "/setup" })
      } catch (e: unknown) {
        if (isRedirect(e)) throw e
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

const pensionDetailRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/accounts/$accountId/pension",
  component: PensionDetail,
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

const fireRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/fire",
  component: Fire,
})

const fireDetailRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/fire/$scenarioId",
  component: FireDetail,
})

const debtRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/debt",
  component: Debt,
})

const settingsExportsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/exports",
  component: ExportsHistory,
})

const settingsBackupsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/backups",
  component: SettingsBackups,
})

const settingsImportsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/imports",
  component: SettingsImports,
})

const settingsDashboardRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/dashboard",
  component: SettingsDashboard,
})

const settingsAppearanceRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/settings/appearance",
  component: SettingsAppearance,
})

const assetsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/assets",
  component: Assets,
})

const reportsInvestmentsRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/reports/investments",
  component: Investments,
})

const reportsRetirementRoute = createRoute({
  getParentRoute: () => appLayoutRoute,
  path: "/reports/retirement",
  component: Retirement,
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
    pensionDetailRoute,
    settingsActivityRoute,
    settingsSecurityRoute,
    fireRoute,
    fireDetailRoute,
    debtRoute,
    settingsExportsRoute,
    settingsBackupsRoute,
    settingsImportsRoute,
    settingsDashboardRoute,
    settingsAppearanceRoute,
    assetsRoute,
    reportsInvestmentsRoute,
    reportsRetirementRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
