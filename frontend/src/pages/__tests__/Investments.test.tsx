import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Investments from "@/pages/Investments"

vi.mock("@tanstack/react-router", () => ({
  useRouterState: (opts: { select: (s: { location: { search: string } }) => unknown }) =>
    opts.select({ location: { search: "" } }),
}))

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: {
    list: vi.fn(() => Promise.resolve([])),
  },
}))

const brokerageAccount = {
  id: "inv1",
  nickname: "Fidelity Brokerage",
  account_type: "investment_brokerage",
  owner_member_id: "m1",
  institution_name: "Fidelity",
  account_number_last4: "9012",
  include_in_net_worth: true,
  is_active: true,
  current_balance: "42000.00",
  balance_as_of: "2026-06-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
}

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(() => Promise.resolve([brokerageAccount])),
  },
}))

// Demo-data extension panels on the Investments page — empty by default so the
// existing assertions are unaffected.
vi.mock("@/api/equityGrants", () => ({
  equityGrantsApi: { list: vi.fn(() => Promise.resolve([])) },
}))
vi.mock("@/api/investmentLots", () => ({
  investmentLotsApi: { list: vi.fn(() => Promise.resolve([])) },
}))
vi.mock("@/api/capitalCommitments", () => ({
  capitalCommitmentsApi: { list: vi.fn(() => Promise.resolve([])) },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Investments />
    </QueryClientProvider>,
  )
}

describe("Investments page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page heading", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Investments" })).toBeInTheDocument()
    })
  })

  it("shows brokerage account name", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Fidelity Brokerage")).toBeInTheDocument()
    })
  })

  it("shows brokerage account balance", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("$42,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows total brokerage KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Total brokerage")).toBeInTheDocument()
    })
  })

  it("shows account count in summary", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("1 brokerage account")).toBeInTheDocument()
    })
  })

  it("shows institution name", async () => {
    renderPage()
    await waitFor(() => {
      // Institution is now combined with the masked account number
      expect(screen.getByText("Fidelity · XXX...9012")).toBeInTheDocument()
    })
  })

  it("shows masked account number", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Fidelity · XXX...9012")).toBeInTheDocument()
    })
  })

  it("shows empty state when no brokerage accounts", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(
        screen.getByText(
          "No brokerage accounts yet. Add an investment brokerage account to get started.",
        ),
      ).toBeInTheDocument()
    })
  })

  it("shows no-snapshot message when account has no history", async () => {
    // Re-set default mock in case the empty-state test ran first and overrode it
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([brokerageAccount])
    renderPage()
    await waitFor(() => screen.getByText("Fidelity Brokerage"))
    await waitFor(() => {
      expect(
        screen.getByText("No snapshot history yet — add snapshots to see the balance chart."),
      ).toBeInTheDocument()
    })
  })
})
