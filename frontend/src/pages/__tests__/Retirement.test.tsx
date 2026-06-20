import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Retirement from "@/pages/Retirement"

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: {
    list: vi.fn(() => Promise.resolve([])),
  },
}))

const retirementAccounts = [
  {
    id: "r1",
    nickname: "Fidelity 401k",
    account_type: "retirement_401k",
    owner_member_id: "m1",
    institution_name: "Fidelity",
    account_number_last4: "1111",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "80000.00",
    balance_as_of: "2026-06-01",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "r2",
    nickname: "Roth IRA",
    account_type: "retirement_roth_ira",
    owner_member_id: "m1",
    institution_name: "Vanguard",
    account_number_last4: "2222",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "30000.00",
    balance_as_of: "2026-06-01",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "r3",
    nickname: "HSA",
    account_type: "hsa",
    owner_member_id: "m1",
    institution_name: "Optum Bank",
    account_number_last4: "3333",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "5000.00",
    balance_as_of: "2026-06-01",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
]

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(() => Promise.resolve(retirementAccounts)),
  },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Retirement />
    </QueryClientProvider>,
  )
}

describe("Retirement page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page heading", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Retirement" })).toBeInTheDocument()
    })
  })

  it("shows Total retirement KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Total retirement")).toBeInTheDocument()
    })
  })

  it("shows combined total ($115,000)", async () => {
    renderPage()
    await waitFor(() => {
      // 80000 + 30000 + 5000 = 115000
      expect(screen.getByText("$115,000.00")).toBeInTheDocument()
    })
  })

  it("shows Tax-deferred group", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("Tax-deferred").length).toBeGreaterThan(0)
    })
  })

  it("shows Tax-free group", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("Tax-free").length).toBeGreaterThan(0)
    })
  })

  it("renders Fidelity 401k in Tax-deferred", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Fidelity 401k")).toBeInTheDocument()
    })
  })

  it("renders Roth IRA in Tax-free", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Roth IRA")).toBeInTheDocument()
    })
  })

  it("renders HSA in Tax-free", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("HSA")).toBeInTheDocument()
    })
  })

  it("shows tax-deferred subtotal ($80,000)", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("$80,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows masked account number in subtitle", async () => {
    renderPage()
    await waitFor(() => {
      // Fidelity 401k: institution · type · masked number
      expect(screen.getByText("Fidelity · 401(k) · XXX...1111")).toBeInTheDocument()
    })
  })

  it("shows empty state when no retirement accounts", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(
        screen.getByText(
          "No retirement accounts yet. Add a 401k, IRA, Roth IRA, HSA, or pension to get started.",
        ),
      ).toBeInTheDocument()
    })
  })
})
