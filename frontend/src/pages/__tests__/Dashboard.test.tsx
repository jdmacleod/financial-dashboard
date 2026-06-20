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
        net_worth: { current: "142500.00", change_30d: "500.00", change_30d_pct: 0.5 },
        cash_flow_mtd: { income: "5000.00", expenses: "3000.00", net: "2000.00" },
        top_spending_categories: [],
        budget_alerts: [],
        accounts_summary: { total_assets: "150000.00", total_liabilities: "7500.00" },
      }),
    ),
    netWorth: vi.fn(() =>
      Promise.resolve({
        series: [
          {
            date: "2026-01-01",
            total_assets: "98000.00",
            total_liabilities: "0.00",
            net_worth: "98000.00",
            breakdown: {
              checking_savings: "10000.00",
              investment: "40000.00",
              retirement: "48000.00",
              real_estate: "0.00",
              hsa: "0.00",
              other_assets: "0.00",
              mortgage: "0.00",
              other_liabilities: "0.00",
            },
          },
        ],
        current: {
          date: "2026-06-01",
          total_assets: "100000.00",
          total_liabilities: "0.00",
          net_worth: "100000.00",
          breakdown: {
            checking_savings: "10000.00",
            investment: "42000.00",
            retirement: "48000.00",
            real_estate: "0.00",
            hsa: "0.00",
            other_assets: "0.00",
            mortgage: "0.00",
            other_liabilities: "0.00",
          },
        },
        pension_annotations: [],
      }),
    ),
    cashFlow: vi.fn(() =>
      Promise.resolve({
        series: [
          {
            period: "2026-01-01",
            income: "5000.00",
            expenses: "3000.00",
            net: "2000.00",
            savings_rate: 40,
          },
        ],
        totals: {
          period: "total",
          income: "5000.00",
          expenses: "3000.00",
          net: "2000.00",
          savings_rate: 40,
        },
      }),
    ),
  },
}))

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(() =>
      Promise.resolve([
        {
          id: "a1",
          nickname: "Chase Checking",
          account_type: "checking",
          owner_member_id: "member-1",
          institution_name: "Chase",
          account_number_last4: "1234",
          include_in_net_worth: true,
          is_active: true,
          current_balance: "8000.00",
          balance_as_of: "2026-06-01",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-06-01T00:00:00Z",
        },
        {
          id: "a2",
          nickname: "Fidelity 401k",
          account_type: "retirement_401k",
          owner_member_id: "member-1",
          institution_name: "Fidelity",
          account_number_last4: "5678",
          include_in_net_worth: true,
          is_active: true,
          current_balance: "48000.00",
          balance_as_of: "2026-06-01",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-06-01T00:00:00Z",
        },
      ]),
    ),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string; memberId: string }) => unknown) =>
    selector({ role: "primary", memberId: "member-1" }),
  ),
}))

const mockUseRouterState = vi.fn(() => "")
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string }>) => (
    <a href={props.to}>{children}</a>
  ),
  useRouterState: (opts: { select: (s: { location: { search: string } }) => unknown }) =>
    opts.select({ location: { search: mockUseRouterState() as string } }),
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

describe("Dashboard — Overview tab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseRouterState.mockReturnValue("")
  })

  it("shows household name as page heading", async () => {
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

  it("shows Net Worth KPI from dashboard API", async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText("$142,500.00")).toBeInTheDocument()
    })
  })

  it("shows liquid balance from checking accounts", async () => {
    renderDashboard()
    await waitFor(() => {
      // $8,000 from Chase Checking — appears in KPI card and holdings list
      expect(screen.getAllByText("$8,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows saved/mo from cash_flow_mtd.net", async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText("$2,000.00")).toBeInTheDocument()
    })
  })

  it("shows largest holding account name", async () => {
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByText("Fidelity 401k")).toBeInTheDocument()
    })
  })

  it("calls netWorth with 1Y date range when range=1y", async () => {
    const { reportsApi: mock } = await import("@/api/reports")
    mockUseRouterState.mockReturnValue("?range=1y")

    renderDashboard()

    await waitFor(() => {
      expect(mock.netWorth).toHaveBeenCalled()
    })

    // For the 1Y range the `from` date is subDays(today, 365) — NOT the start of the
    // current year (which is what YTD uses). Assert the from year/month is ~1 year ago.
    const [fromArg] = (mock.netWorth as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      string,
      string,
    ]
    const fromDate = new Date(fromArg)
    const oneYearAgo = new Date()
    oneYearAgo.setDate(oneYearAgo.getDate() - 365)
    // Allow ±2 days tolerance for test timing
    expect(Math.abs(fromDate.getTime() - oneYearAgo.getTime())).toBeLessThan(
      2 * 24 * 60 * 60 * 1000,
    )
  })
})
