import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import type { AccountResponse } from "@/api/types"

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(),
    create: vi.fn(),
    deactivate: vi.fn(),
    listGrants: vi.fn(),
    createGrant: vi.fn(),
    revokeGrant: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string }>) => (
    <a href={props.to}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string }) => unknown) => selector({ role: "primary" })),
}))

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderWithClient(ui: React.ReactElement) {
  return render(<QueryClientProvider client={createClient()}>{ui}</QueryClientProvider>)
}

const makeAccount = (overrides: Partial<AccountResponse>): AccountResponse => ({
  id: "acc-1",
  nickname: "My Account",
  account_type: "checking",
  owner_member_id: null,
  institution_name: null,
  account_number_last4: null,
  include_in_net_worth: true,
  is_active: true,
  current_balance: "1000.00",
  balance_as_of: "2026-06-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
})

describe("Accounts page — DISPLAY_ASSET_TYPES filter (F3)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows checking and savings accounts", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAccount({ id: "acc-1", nickname: "Chase Checking", account_type: "checking" }),
      makeAccount({ id: "acc-2", nickname: "Ally Savings", account_type: "savings" }),
    ])

    const { default: Accounts } = await import("@/pages/Accounts")
    renderWithClient(<Accounts />)

    await waitFor(() => {
      expect(screen.getByText("Chase Checking")).toBeInTheDocument()
      expect(screen.getByText("Ally Savings")).toBeInTheDocument()
    })
  })

  it("hides investment types from the Accounts list", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAccount({ id: "acc-1", nickname: "Chase Checking", account_type: "checking" }),
      makeAccount({ id: "acc-2", nickname: "Vanguard 401k", account_type: "retirement_401k" }),
      makeAccount({ id: "acc-3", nickname: "Brokerage", account_type: "investment_brokerage" }),
      makeAccount({ id: "acc-4", nickname: "My Home", account_type: "real_estate" }),
      makeAccount({ id: "acc-5", nickname: "State Pension", account_type: "pension" }),
    ])

    const { default: Accounts } = await import("@/pages/Accounts")
    renderWithClient(<Accounts />)

    await waitFor(() => {
      expect(screen.getByText("Chase Checking")).toBeInTheDocument()
    })

    expect(screen.queryByText("Vanguard 401k")).not.toBeInTheDocument()
    expect(screen.queryByText("Brokerage")).not.toBeInTheDocument()
    expect(screen.queryByText("My Home")).not.toBeInTheDocument()
    expect(screen.queryByText("State Pension")).not.toBeInTheDocument()
  })
})
