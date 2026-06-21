import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Accounts from "@/pages/Accounts"

const mockNavigate = vi.fn()

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string; params?: unknown }>) => (
    <a href={String(props.to)}>{children}</a>
  ),
  useNavigate: () => mockNavigate,
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string; memberId: string }) => unknown) =>
    selector({ role: "primary", memberId: "m1" }),
  ),
}))

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: {
    list: vi.fn(() => Promise.resolve([])),
  },
}))

const mockAccounts = [
  {
    id: "a1",
    nickname: "Chase Checking",
    account_type: "checking",
    owner_member_id: "m1",
    institution_name: "Chase",
    account_number_last4: "1234",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "8000.00",
    balance_as_of: "2026-06-01",
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "a2",
    nickname: "Fidelity 401k",
    account_type: "retirement_401k",
    owner_member_id: "m1",
    institution_name: "Fidelity",
    account_number_last4: "5678",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "48000.00",
    balance_as_of: "2026-06-01",
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
  {
    id: "a3",
    nickname: "Chase Visa",
    account_type: "credit_card",
    owner_member_id: "m1",
    institution_name: "Chase",
    account_number_last4: "9999",
    include_in_net_worth: true,
    is_active: true,
    current_balance: "-1500.00",
    balance_as_of: "2026-06-01",
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  },
]

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(() => Promise.resolve(mockAccounts)),
    update: vi.fn(() => Promise.resolve({})),
  },
}))

vi.mock("@/components/app/AddAccountModal", () => ({
  default: ({ onClose, allowedTypes }: { onClose: () => void; allowedTypes?: string[] }) => (
    <div data-testid="add-account-modal" data-allowed-types={(allowedTypes ?? []).join(",")}>
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

vi.mock("@/components/app/EditAccountModal", () => ({
  default: ({ onClose }: { onClose: () => void }) => (
    <div data-testid="edit-account-modal">
      <button onClick={onClose}>Close</button>
    </div>
  ),
}))

function renderAccounts() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Accounts />
    </QueryClientProvider>,
  )
}

describe("Accounts — split-panel ledger", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
    // Restore default mock implementations that may have been overridden by individual tests
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue(mockAccounts)
    const { useAuth: mockUseAuth } = await import("@/hooks/useAuth")
    ;(mockUseAuth as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      (selector: (s: { role: string; memberId: string }) => unknown) =>
        selector({ role: "primary", memberId: "m1" }),
    )
  })

  it("renders page heading", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Accounts")).toBeInTheDocument()
    })
  })

  it("shows Banking & Cash category group", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Banking & Cash")).toBeInTheDocument()
    })
  })

  it("shows Retirement category group", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Retirement")).toBeInTheDocument()
    })
  })

  it("shows Liabilities category group", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Liabilities")).toBeInTheDocument()
    })
  })

  it("renders Chase Checking in the list", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Chase Checking")).toBeInTheDocument()
    })
  })

  it("renders Fidelity 401k in the list", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Fidelity 401k")).toBeInTheDocument()
    })
  })

  it("renders Chase Visa in Liabilities", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("Chase Visa")).toBeInTheDocument()
    })
  })

  it("shows Add account button for primary role", async () => {
    renderAccounts()
    await waitFor(() => {
      expect(screen.getByText("+ Add account")).toBeInTheDocument()
    })
  })

  it("opens add account modal when + Add account is clicked", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("+ Add account"))
    await user.click(screen.getByText("+ Add account"))
    expect(screen.getByTestId("add-account-modal")).toBeInTheDocument()
  })

  it("shows detail panel when an account is selected", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getByText("View transactions →")).toBeInTheDocument()
    })
  })

  it("hides detail panel when same account is clicked again", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("View transactions →"))
    // Detail panel is now open: "Chase Checking" appears in both the list row and the panel header.
    // Click the first occurrence (the list row button) to deselect.
    await user.click(screen.getAllByText("Chase Checking")[0])
    await waitFor(() => {
      expect(screen.queryByText("View transactions →")).not.toBeInTheDocument()
    })
  })

  it("shows balance in detail panel", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getAllByText("$8,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows archive button in detail panel for primary role", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getByText("Archive")).toBeInTheDocument()
    })
  })

  it("opens archive modal when Archive is clicked", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("Archive"))
    await user.click(screen.getByText("Archive"))
    expect(screen.getByTestId("archive-account-modal")).toBeInTheDocument()
  })

  it("shows Edit button in detail panel for primary role", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getByText("Edit")).toBeInTheDocument()
    })
  })

  it("opens edit modal when Edit is clicked", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("Edit"))
    await user.click(screen.getByText("Edit"))
    expect(screen.getByTestId("edit-account-modal")).toBeInTheDocument()
  })

  it("shows masked account number in list row subtitle", async () => {
    renderAccounts()
    await waitFor(() => {
      // Chase Checking: institution · type · masked number
      expect(screen.getByText("Chase · Checking · XXX...1234")).toBeInTheDocument()
    })
  })

  it("shows masked account number in detail panel", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getByText("XXX...1234")).toBeInTheDocument()
    })
  })

  it("shows empty state when no accounts", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([])
    renderAccounts()
    await waitFor(() => {
      expect(
        screen.getByText("No accounts yet. Add your first account to get started."),
      ).toBeInTheDocument()
    })
  })

  it("does not show Notes section in detail panel when account.notes is null", async () => {
    const user = userEvent.setup()
    // mockAccounts[0] has notes: null
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("View transactions →"))
    expect(screen.queryByText("Notes")).not.toBeInTheDocument()
  })

  it("shows Notes section in detail panel when account.notes is non-null", async () => {
    const user = userEvent.setup()
    const { accountsApi: mock } = await import("@/api/accounts")
    const accountsWithNotes = mockAccounts.map((a) =>
      a.id === "a1" ? { ...a, notes: "My primary daily account" } : a,
    )
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue(accountsWithNotes)

    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => {
      expect(screen.getByText("Notes")).toBeInTheDocument()
      expect(screen.getByText("My primary daily account")).toBeInTheDocument()
    })
  })

  it("does not show Edit button in detail panel for partner role", async () => {
    const { useAuth: mockUseAuth } = await import("@/hooks/useAuth")
    ;(mockUseAuth as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      (selector: (s: { role: string; memberId: string }) => unknown) =>
        selector({ role: "partner", memberId: "m1" }),
    )

    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("View transactions →"))
    expect(screen.queryByText("Edit")).not.toBeInTheDocument()
    expect(screen.queryByText("Archive")).not.toBeInTheDocument()
  })

  it("does not show Edit or Archive buttons in detail panel for view_only role", async () => {
    const { useAuth: mockUseAuth } = await import("@/hooks/useAuth")
    ;(mockUseAuth as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      (selector: (s: { role: string; memberId: string }) => unknown) =>
        selector({ role: "view_only", memberId: "m1" }),
    )

    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Chase Checking"))
    await user.click(screen.getByText("Chase Checking"))
    await waitFor(() => screen.getByText("View transactions →"))
    expect(screen.queryByText("Edit")).not.toBeInTheDocument()
    expect(screen.queryByText("Archive")).not.toBeInTheDocument()
  })

  it("Banking & Cash + opens modal filtered to banking types only", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Banking & Cash"))
    await user.click(screen.getByRole("button", { name: "Add Banking & Cash account" }))
    const modal = screen.getByTestId("add-account-modal")
    expect(modal).toBeInTheDocument()
    const types = modal.getAttribute("data-allowed-types") ?? ""
    expect(types).toContain("checking")
    expect(types).toContain("savings")
    expect(types).not.toContain("credit_card")
    expect(types).not.toContain("retirement")
  })

  it("Liabilities + opens modal filtered to liability types only", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Liabilities"))
    await user.click(screen.getByRole("button", { name: "Add Liabilities account" }))
    const modal = screen.getByTestId("add-account-modal")
    expect(modal).toBeInTheDocument()
    const types = modal.getAttribute("data-allowed-types") ?? ""
    expect(types).toContain("credit_card")
    expect(types).toContain("mortgage")
    expect(types).not.toContain("checking")
    expect(types).not.toContain("savings")
  })

  it("Retirement + navigates to /reports/retirement without opening modal", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Retirement"))
    await user.click(screen.getByRole("button", { name: "Add Retirement account" }))
    expect(mockNavigate).toHaveBeenCalledWith({ to: "/reports/retirement" })
    expect(screen.queryByTestId("add-account-modal")).not.toBeInTheDocument()
  })

  it("Investments + navigates to /reports/investments without opening modal", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      ...mockAccounts,
      {
        id: "a5",
        nickname: "Fidelity Brokerage",
        account_type: "investment_brokerage",
        owner_member_id: "m1",
        institution_name: "Fidelity",
        account_number_last4: "4444",
        include_in_net_worth: true,
        is_active: true,
        current_balance: "25000.00",
        balance_as_of: "2026-06-01",
        notes: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-06-01T00:00:00Z",
      },
    ])
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Investments"))
    await user.click(screen.getByRole("button", { name: "Add Investments account" }))
    expect(mockNavigate).toHaveBeenCalledWith({ to: "/reports/investments" })
    expect(screen.queryByTestId("add-account-modal")).not.toBeInTheDocument()
  })

  it("Real estate + navigates to /assets without opening modal", async () => {
    const { accountsApi: mock } = await import("@/api/accounts")
    ;(mock.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      ...mockAccounts,
      {
        id: "a4",
        nickname: "Main Home",
        account_type: "real_estate",
        owner_member_id: "m1",
        institution_name: null,
        account_number_last4: null,
        include_in_net_worth: true,
        is_active: true,
        current_balance: "450000.00",
        balance_as_of: "2026-06-01",
        notes: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-06-01T00:00:00Z",
      },
    ])
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Real estate"))
    await user.click(screen.getByRole("button", { name: "Add Real estate account" }))
    expect(mockNavigate).toHaveBeenCalledWith({ to: "/assets" })
    expect(screen.queryByTestId("add-account-modal")).not.toBeInTheDocument()
  })

  it("closing the add modal resets addFilter so the header button uses full ACCOUNTS_PAGE_TYPES", async () => {
    const user = userEvent.setup()
    renderAccounts()
    await waitFor(() => screen.getByText("Banking & Cash"))
    // Open via category button (banking filter)
    await user.click(screen.getByRole("button", { name: "Add Banking & Cash account" }))
    const modal1 = screen.getByTestId("add-account-modal")
    const types1 = modal1.getAttribute("data-allowed-types") ?? ""
    expect(types1).not.toContain("credit_card")
    // Close modal
    await user.click(screen.getByText("Close"))
    expect(screen.queryByTestId("add-account-modal")).not.toBeInTheDocument()
    // Re-open via header button (should use ACCOUNTS_PAGE_TYPES — includes both banking and liability types)
    await user.click(screen.getByText("+ Add account"))
    const modal2 = screen.getByTestId("add-account-modal")
    const types2 = modal2.getAttribute("data-allowed-types") ?? ""
    expect(types2).toContain("checking")
    expect(types2).toContain("credit_card")
  })
})
