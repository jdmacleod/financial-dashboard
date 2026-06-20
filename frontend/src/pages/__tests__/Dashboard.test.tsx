import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Dashboard from "@/pages/Dashboard"

vi.mock("@/api/members", () => ({
  membersApi: {
    get: vi.fn(() =>
      Promise.resolve({
        id: "member-1",
        household_id: "hh-1",
        display_name: "Jason MacLeod",
        role: "primary",
        date_of_birth: null,
        is_active: true,
        settings: {},
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      }),
    ),
  },
}))

vi.mock("@/api/household", () => ({
  householdApi: {
    get: vi.fn(() =>
      Promise.resolve({
        id: "hh-1",
        name: "MacLeod Household",
        settings: {},
        created_at: "2026-01-01T00:00:00Z",
      }),
    ),
  },
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    dashboard: vi.fn(() =>
      Promise.resolve({
        net_worth: { current: "100000.00", change_30d: "500.00", change_30d_pct: 0.5 },
        cash_flow_mtd: { income: "5000.00", expenses: "3000.00", net: "2000.00" },
        top_spending_categories: [],
        budget_alerts: [],
        accounts_summary: { total_assets: "100000.00", total_liabilities: "0.00" },
      }),
    ),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string; memberId: string }) => unknown) =>
    selector({ role: "primary", memberId: "member-1" }),
  ),
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string }>) => (
    <a href={props.to}>{children}</a>
  ),
}))

function renderDashboard() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Dashboard />
    </QueryClientProvider>,
  )
}

describe("Dashboard — householdName title (F1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows household name as page title when loaded", async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "MacLeod Household" })).toBeInTheDocument()
    })
  })

  it("falls back to 'Dashboard' when householdName is null", async () => {
    const { householdApi: mock } = await import("@/api/household")
    ;(mock.get as ReturnType<typeof vi.fn>).mockResolvedValue(null)

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument()
    })
  })
})
