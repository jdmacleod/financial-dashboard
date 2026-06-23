import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Assets from "@/pages/Assets"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string; params?: unknown }>) => (
    <a href={String(props.to)}>{children}</a>
  ),
  useRouterState: (opts: { select: (s: { location: { search: string } }) => unknown }) =>
    opts.select({ location: { search: "" } }),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string }) => unknown) => selector({ role: "primary" })),
}))

const mockProperty = {
  id: "prop-1",
  account_id: "re-1",
  nickname: "My Home",
  address: "123 Main St, Springfield",
  purchase_date: "2020-06-01",
  purchase_price: "350000.00",
  linked_mortgage_account_id: "mort-1",
  property_type: "primary_residence",
  current_estimated_value: "420000.00",
  current_value_as_of: "2026-06-01",
  gain_loss: "70000.00",
  gain_loss_pct: "20.00",
  created_at: "2020-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
}

const mockEquity = {
  property_value: "420000.00",
  valuation_date: "2026-06-01",
  valuation_source: "manual",
  mortgage_balance: "280000.00",
  mortgage_balance_as_of: "2026-06-01",
  mortgage_balance_visible: true,
  equity: "140000.00",
}

const mockValuations = [
  {
    id: "v1",
    real_estate_property_id: "prop-1",
    valuation_date: "2026-06-01",
    estimated_value: "420000.00",
    source: "manual" as const,
    confidence_score: null,
    created_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "v2",
    real_estate_property_id: "prop-1",
    valuation_date: "2025-06-01",
    estimated_value: "400000.00",
    source: "manual" as const,
    confidence_score: null,
    created_at: "2025-06-01T00:00:00Z",
  },
]

vi.mock("@/api/properties", () => ({
  propertiesApi: {
    getByAccountId: vi.fn(() => Promise.resolve(mockProperty)),
    getEquity: vi.fn(() => Promise.resolve(mockEquity)),
    listValuations: vi.fn(() => Promise.resolve(mockValuations)),
  },
}))

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(() =>
      Promise.resolve([
        {
          id: "re-1",
          nickname: "My Home",
          account_type: "real_estate",
          owner_member_id: "m1",
          institution_name: null,
          account_number_last4: null,
          include_in_net_worth: true,
          is_active: true,
          current_balance: "420000.00",
          balance_as_of: "2026-06-01",
          created_at: "2020-06-01T00:00:00Z",
          updated_at: "2026-06-01T00:00:00Z",
        },
      ]),
    ),
  },
}))

vi.mock("@/components/app/AddAccountModal", () => ({
  default: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="add-account-modal">
      <button onClick={onClose}>Close</button>
    </div>
  ),
}))

vi.mock("@/components/app/ArchiveAccountModal", () => ({
  default: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="archive-account-modal">
      <button onClick={onClose}>Close</button>
    </div>
  ),
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Assets />
    </QueryClientProvider>,
  )
}

describe("Assets — Real estate tab (Phase 6)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page heading", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Real estate")).toBeInTheDocument()
    })
  })

  it("shows the property nickname", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("My Home").length).toBeGreaterThan(0)
    })
  })

  it("shows property address", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/123 Main St/)).toBeInTheDocument()
    })
  })

  it("shows current estimated value", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("$420,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows equity figure", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("$140,000.00")).toBeInTheDocument()
    })
  })

  it("shows mortgage balance", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/\$280,000\.00 mortgage/)).toBeInTheDocument()
    })
  })

  it("shows View property link", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("View property →")).toBeInTheDocument()
    })
  })

  it("shows + Add property button for primary role", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("+ Add property")).toBeInTheDocument()
    })
  })

  it("opens add account modal when + Add property is clicked", async () => {
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByText("+ Add property"))
    await user.click(screen.getByText("+ Add property"))
    expect(screen.getByTestId("add-account-modal")).toBeInTheDocument()
  })

  it("shows archive button and opens archive modal", async () => {
    const user = userEvent.setup()
    renderPage()
    await waitFor(() => screen.getByText("Archive"))
    await user.click(screen.getByText("Archive"))
    expect(screen.getByTestId("archive-account-modal")).toBeInTheDocument()
  })

  it("shows total property value KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Total property value")).toBeInTheDocument()
    })
  })

  it("shows property count in summary", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("1 property")).toBeInTheDocument()
    })
  })

  it("renders equity for a property with no linked mortgage (cash purchase)", async () => {
    // H5 Langford's Sarasota home is a cash purchase: linked_mortgage_account_id
    // is null and the equity endpoint reports no mortgage balance. The equity
    // display must render the full property value as equity without a mortgage
    // line and without crashing.
    const { accountsApi: accounts } = await import("@/api/accounts")
    const { propertiesApi: properties } = await import("@/api/properties")
    ;(accounts.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        id: "re-2",
        nickname: "Sarasota Home",
        account_type: "real_estate",
        owner_member_id: "m1",
        institution_name: null,
        account_number_last4: null,
        include_in_net_worth: true,
        is_active: true,
        current_balance: "650000.00",
        balance_as_of: "2026-06-01",
        created_at: "2018-03-01T00:00:00Z",
        updated_at: "2026-06-01T00:00:00Z",
      },
    ])
    ;(properties.getByAccountId as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockProperty,
      id: "prop-2",
      account_id: "re-2",
      nickname: "Sarasota Home",
      address: "456 Beach Dr, Sarasota",
      linked_mortgage_account_id: null,
      purchase_price: "650000.00",
      current_estimated_value: "650000.00",
      gain_loss: "0.00",
      gain_loss_pct: "0.00",
    })
    ;(properties.getEquity as ReturnType<typeof vi.fn>).mockResolvedValue({
      property_value: "650000.00",
      valuation_date: "2026-06-01",
      valuation_source: "manual",
      mortgage_balance: null,
      mortgage_balance_as_of: null,
      mortgage_balance_visible: false,
      equity: "650000.00",
    })
    ;(properties.listValuations as ReturnType<typeof vi.fn>).mockResolvedValue([])

    renderPage()

    await waitFor(() => {
      expect(screen.getAllByText("$650,000.00").length).toBeGreaterThan(0)
    })
    // No mortgage line should be rendered for a cash-purchased property.
    expect(screen.queryByText(/mortgage/i)).toBeNull()
  })

  it("shows empty state when no real estate accounts", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([])
    renderPage()
    await waitFor(() => {
      expect(
        screen.getByText("No properties yet. Add a real estate account to get started."),
      ).toBeInTheDocument()
    })
  })
})
