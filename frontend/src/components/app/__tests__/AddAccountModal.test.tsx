import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import AddAccountModal from "../AddAccountModal"
import { accountsApi } from "@/api/accounts"
import { membersApi } from "@/api/members"
import { snapshotsApi } from "@/api/snapshots"
import { transactionsApi } from "@/api/transactions"
import { createClient, wrapper } from "@/test/testUtils"
import type { AccountResponse, AccountType, MemberResponse } from "@/api/types"

vi.mock("@/api/accounts", () => ({
  accountsApi: { create: vi.fn(), list: vi.fn() },
}))
vi.mock("@/api/members", () => ({ membersApi: { list: vi.fn() } }))
vi.mock("@/api/properties", () => ({ propertiesApi: { create: vi.fn() } }))
vi.mock("@/api/snapshots", () => ({ snapshotsApi: { create: vi.fn() } }))
vi.mock("@/api/transactions", () => ({ transactionsApi: { create: vi.fn() } }))
vi.mock("@/hooks/useAuth", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuth: vi.fn((selector: any) => selector({ role: "primary", memberId: "m1" })),
}))

const soloMember: MemberResponse = {
  id: "m1",
  household_id: "h1",
  display_name: "Solo",
  role: "primary",
  date_of_birth: null,
  retirement_target_age: null,
  ss_monthly_benefit_at_fra: null,
  ss_claiming_age: null,
  is_active: true,
  settings: {},
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
}

const newAccount = (overrides: Partial<AccountResponse> = {}): AccountResponse => ({
  id: "new-1",
  nickname: "X",
  account_type: "checking",
  owner_member_id: null,
  ownership_entity_id: null,
  institution_name: null,
  account_number_last4: null,
  include_in_net_worth: true,
  tax_treatment: null,
  is_active: true,
  current_balance: null,
  balance_as_of: null,
  notes: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...overrides,
})

const ALLOWED: AccountType[] = ["checking", "mortgage", "retirement_ira"]

function renderModal(onClose = vi.fn()) {
  const client = createClient()
  render(<AddAccountModal allowedTypes={ALLOWED} onClose={onClose} />, { wrapper: wrapper(client) })
  return { onClose }
}

async function pickType(user: ReturnType<typeof userEvent.setup>, label: string) {
  // Single-member household opens directly on the type-selection step.
  await screen.findByRole("button", { name: label })
  await user.click(screen.getByRole("button", { name: label }))
}

describe("AddAccountModal — initial balance", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(membersApi.list).mockResolvedValue([soloMember])
    vi.mocked(accountsApi.list).mockResolvedValue([])
  })

  it("records a negative opening transaction for a liability (mortgage)", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.create).mockResolvedValue(newAccount({ account_type: "mortgage" }))
    vi.mocked(transactionsApi.create).mockResolvedValue({} as never)

    renderModal()
    await pickType(user, "Mortgage")

    await user.type(screen.getByPlaceholderText("e.g. BofA Checking"), "New Mortgage")
    // Liability field is labelled "Balance owed"; user enters the magnitude.
    await user.type(screen.getByPlaceholderText("e.g. 298700.00"), "298700")
    await user.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => {
      expect(transactionsApi.create).toHaveBeenCalledWith(
        "new-1",
        expect.objectContaining({
          amount: "-298700.00",
          payee_normalized: "Opening balance",
          is_transfer: true,
        }),
      )
    })
    expect(snapshotsApi.create).not.toHaveBeenCalled()
  })

  it("records a positive opening transaction for a cash asset (checking)", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.create).mockResolvedValue(newAccount({ account_type: "checking" }))
    vi.mocked(transactionsApi.create).mockResolvedValue({} as never)

    renderModal()
    await pickType(user, "Checking")

    await user.type(screen.getByPlaceholderText("e.g. BofA Checking"), "Everyday")
    await user.type(screen.getByPlaceholderText("e.g. 298700.00"), "5000")
    await user.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => {
      expect(transactionsApi.create).toHaveBeenCalledWith(
        "new-1",
        expect.objectContaining({ amount: "5000.00" }),
      )
    })
  })

  it("records a snapshot (not a transaction) for a valuation-based account (IRA)", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.create).mockResolvedValue(newAccount({ account_type: "retirement_ira" }))
    vi.mocked(snapshotsApi.create).mockResolvedValue({} as never)

    renderModal()
    await pickType(user, "IRA")

    await user.type(screen.getByPlaceholderText("e.g. BofA Checking"), "Rollover IRA")
    await user.type(screen.getByPlaceholderText("e.g. 298700.00"), "100000")
    await user.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => {
      expect(snapshotsApi.create).toHaveBeenCalledWith(
        "new-1",
        expect.objectContaining({ balance: "100000.00" }),
      )
    })
    expect(transactionsApi.create).not.toHaveBeenCalled()
  })

  it("creates the account with no opening entry when balance is left blank", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.create).mockResolvedValue(newAccount({ account_type: "checking" }))

    renderModal()
    await pickType(user, "Checking")

    await user.type(screen.getByPlaceholderText("e.g. BofA Checking"), "Empty")
    await user.click(screen.getByRole("button", { name: /add account/i }))

    await waitFor(() => expect(accountsApi.create).toHaveBeenCalled())
    expect(transactionsApi.create).not.toHaveBeenCalled()
    expect(snapshotsApi.create).not.toHaveBeenCalled()
  })
})
