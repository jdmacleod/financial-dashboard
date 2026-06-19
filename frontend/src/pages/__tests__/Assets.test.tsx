import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Assets from "@/pages/Assets"
import { accountsApi } from "@/api/accounts"
import { snapshotsApi } from "@/api/snapshots"
import type { AccountResponse } from "@/api/types"

vi.mock("@/api/accounts", () => ({
  accountsApi: { list: vi.fn() },
}))

vi.mock("@/api/properties", () => ({
  propertiesApi: { getByAccountId: vi.fn(() => Promise.resolve(null)) },
}))

vi.mock("@/api/pension", () => ({
  pensionApi: { get: vi.fn(() => Promise.resolve(null)) },
}))

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: { create: vi.fn() },
}))

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <a href={String(props.to ?? "#")}>{children}</a>
  ),
}))

const mockList = vi.mocked(accountsApi.list)
const mockCreate = vi.mocked(snapshotsApi.create)

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderAssets() {
  return render(
    <QueryClientProvider client={createClient()}>
      <Assets />
    </QueryClientProvider>,
  )
}

const makeAccount = (overrides: Partial<AccountResponse>): AccountResponse => ({
  id: "acc-1",
  nickname: "Test Account",
  account_type: "checking",
  owner_member_id: null,
  institution_name: null,
  account_number_last4: null,
  include_in_net_worth: true,
  is_active: true,
  current_balance: "5000.00",
  balance_as_of: "2026-06-01",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
})

describe("Assets page — account type filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows investment accounts with Update value button", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-1", nickname: "Vanguard IRA", account_type: "retirement_ira" }),
      makeAccount({ id: "acc-2", nickname: "Fidelity 401k", account_type: "retirement_401k" }),
    ])

    renderAssets()

    await waitFor(() => {
      expect(screen.getByText("Vanguard IRA")).toBeInTheDocument()
      expect(screen.getByText("Fidelity 401k")).toBeInTheDocument()
    })

    const buttons = screen.getAllByRole("button", { name: /update value/i })
    expect(buttons).toHaveLength(2)
  })

  it("renders empty state for investments when none present", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-1", nickname: "Chase Checking", account_type: "checking" }),
    ])

    renderAssets()

    await waitFor(() => {
      expect(screen.getByText(/No investment accounts yet/i)).toBeInTheDocument()
    })
  })

  it("routes RE accounts to Real Estate section, not Investments", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-re", nickname: "My Home", account_type: "real_estate" }),
    ])

    renderAssets()

    await waitFor(() => {
      expect(screen.getByText("My Home")).toBeInTheDocument()
    })

    // "My Home" should appear in the RE section, not as an investment row
    expect(screen.queryByRole("button", { name: /update value/i })).not.toBeInTheDocument()
  })
})

describe("UpdateValueModal — decimal validation", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("rejects non-numeric and 5-decimal-place input", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-hsa", nickname: "HSA Account", account_type: "hsa" }),
    ])

    renderAssets()

    await waitFor(() => screen.getByText("HSA Account"))
    fireEvent.click(screen.getByRole("button", { name: /update value/i }))
    await waitFor(() => screen.getByText(/Balance \(\$\)/i))

    const balanceInput = screen.getByPlaceholderText(/e\.g\. 12500/i)
    const submitButton = screen.getByRole("button", { name: /save/i })

    // Non-numeric
    fireEvent.change(balanceInput, { target: { value: "abc" } })
    fireEvent.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/valid amount/i)).toBeInTheDocument()
    })

    // 5 decimal places — too many
    fireEvent.change(balanceInput, { target: { value: "1000.12345" } })
    fireEvent.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/valid amount/i)).toBeInTheDocument()
    })
  })

  it("accepts a valid decimal and calls snapshotsApi.create", async () => {
    mockList.mockResolvedValue([
      makeAccount({
        id: "acc-brok",
        nickname: "Schwab Brokerage",
        account_type: "investment_brokerage",
      }),
    ])
    mockCreate.mockResolvedValue({
      id: "snap-1",
      account_id: "acc-brok",
      snapshot_date: "2026-06-19",
      balance: "25000.00",
      contributed_ytd: null,
      employer_match_ytd: null,
      memo: null,
      source: "manual",
    })

    renderAssets()

    await waitFor(() => screen.getByText("Schwab Brokerage"))
    fireEvent.click(screen.getByRole("button", { name: /update value/i }))
    await waitFor(() => screen.getByPlaceholderText(/e\.g\. 12500/i))

    const balanceInput = screen.getByPlaceholderText(/e\.g\. 12500/i)
    fireEvent.change(balanceInput, { target: { value: "25000.00" } })
    fireEvent.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        "acc-brok",
        expect.objectContaining({ balance: "25000.00" }),
      )
    })
  })

  it("shows error message when snapshotsApi.create fails", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-401k", nickname: "Company 401k", account_type: "retirement_401k" }),
    ])
    mockCreate.mockRejectedValue(new Error("Network error"))

    renderAssets()

    await waitFor(() => screen.getByText("Company 401k"))
    fireEvent.click(screen.getByRole("button", { name: /update value/i }))
    await waitFor(() => screen.getByPlaceholderText(/e\.g\. 12500/i))

    fireEvent.change(screen.getByPlaceholderText(/e\.g\. 12500/i), {
      target: { value: "50000" },
    })
    fireEvent.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText(/Failed to save value/i)).toBeInTheDocument()
    })
  })
})

describe("Assets page — Pension section", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders pension account in the Pension section", async () => {
    mockList.mockResolvedValue([
      makeAccount({ id: "acc-pension", nickname: "State Pension", account_type: "pension" }),
    ])

    const { pensionApi: mockPension } = await import("@/api/pension")
    ;(mockPension.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "p-1",
      account_id: "acc-pension",
      member_id: null,
      plan_name: "State Teachers Retirement",
      administrator: null,
      monthly_benefit_estimate: "3000.00",
      eligibility_age: 62,
      eligibility_date: null,
      cola_adjustment_rate: "0",
      is_vested: true,
      vesting_date: null,
      survivor_benefit_percent: null,
      notes: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    })

    renderAssets()

    await waitFor(() => {
      expect(screen.getByText("State Pension")).toBeInTheDocument()
    })

    // Pension section heading
    expect(screen.getByText(/Pensions/i)).toBeInTheDocument()
    // No "Update value" button — pensions are not investment rows
    expect(screen.queryByRole("button", { name: /update value/i })).not.toBeInTheDocument()
  })
})
