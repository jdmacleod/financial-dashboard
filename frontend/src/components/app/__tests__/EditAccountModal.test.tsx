import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import EditAccountModal from "../EditAccountModal"
import { accountsApi } from "@/api/accounts"
import { useAuth } from "@/hooks/useAuth"
import { ApiError } from "@/api/client"
import { createClient, wrapper } from "@/test/testUtils"
import type { AccountResponse } from "@/api/types"

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    update: vi.fn(),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuth: vi.fn((selector: any) => selector({ role: "primary" })),
}))

const mockAccount: AccountResponse = {
  id: "acct-1",
  nickname: "Chase Checking",
  account_type: "checking",
  owner_member_id: "m1",
  ownership_entity_id: null,
  institution_name: "Chase",
  account_number_last4: "1234",
  include_in_net_worth: true,
  tax_treatment: null,
  is_active: true,
  current_balance: "8000.00",
  balance_as_of: "2026-06-01",
  notes: "Primary everyday account",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
}

function renderModal(account = mockAccount, onClose = vi.fn()) {
  const client = createClient()
  return {
    onClose,
    ...render(<EditAccountModal account={account} onClose={onClose} />, {
      wrapper: wrapper(client),
    }),
  }
}

describe("EditAccountModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders pre-filled form fields from account prop", () => {
    renderModal()
    expect((screen.getByPlaceholderText("e.g. Chase Checking") as HTMLInputElement).value).toBe(
      "Chase Checking",
    )
    expect((screen.getByPlaceholderText("e.g. Chase Bank") as HTMLInputElement).value).toBe("Chase")
    expect(
      (screen.getByPlaceholderText("Optional notes about this account") as HTMLTextAreaElement)
        .value,
    ).toBe("Primary everyday account")
    expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(true)
  })

  it("submits form and closes modal on success", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    vi.mocked(accountsApi.update).mockResolvedValue({
      ...mockAccount,
      nickname: "Chase Checking Updated",
    })

    renderModal(mockAccount, onClose)

    const nicknameInput = screen.getByPlaceholderText("e.g. Chase Checking")
    await user.clear(nicknameInput)
    await user.type(nicknameInput, "Chase Checking Updated")

    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ nickname: "Chase Checking Updated" }),
      )
      expect(onClose).toHaveBeenCalled()
    })
  })

  it("shows error message when mutation fails", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.update).mockRejectedValue(new ApiError(500, "Server error"))

    renderModal()

    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText("Failed to save. Please try again.")).toBeInTheDocument()
    })
  })

  it("shows validation error when nickname is cleared", async () => {
    const user = userEvent.setup()
    renderModal()

    const nicknameInput = screen.getByPlaceholderText("e.g. Chase Checking")
    await user.clear(nicknameInput)
    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText("Required")).toBeInTheDocument()
    })
    // update should not have been called
    expect(accountsApi.update).not.toHaveBeenCalled()
  })

  it("calls onClose when Escape key is pressed", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderModal(mockAccount, onClose)

    await user.keyboard("{Escape}")

    expect(onClose).toHaveBeenCalled()
  })

  it("calls onClose when overlay backdrop is clicked", () => {
    const onClose = vi.fn()
    renderModal(mockAccount, onClose)

    // Click directly on the overlay element (not a child). In JSDOM, fireEvent.click(el)
    // dispatches with e.target === el, which satisfies the `e.target === overlayRef.current`
    // guard in the component's onOverlayClick handler.
    const overlayEl = screen.getByTestId("modal-overlay")
    fireEvent.click(overlayEl)

    expect(onClose).toHaveBeenCalled()
  })

  it("calls onClose when Cancel button is clicked", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderModal(mockAccount, onClose)

    await user.click(screen.getByRole("button", { name: /cancel/i }))

    expect(onClose).toHaveBeenCalled()
  })

  it("calls onClose when × close button is clicked", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderModal(mockAccount, onClose)

    await user.click(screen.getByRole("button", { name: "Close" }))

    expect(onClose).toHaveBeenCalled()
  })

  it("passes notes as null when notes textarea is empty", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    vi.mocked(accountsApi.update).mockResolvedValue(mockAccount)

    const accountWithNotes: AccountResponse = { ...mockAccount, notes: "some note" }
    renderModal(accountWithNotes, onClose)

    const notesArea = screen.getByPlaceholderText("Optional notes about this account")
    await user.clear(notesArea)
    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ notes: null }),
      )
    })
  })

  it("shows account number field with last-4 placeholder for primary role", () => {
    renderModal()
    expect(screen.getByPlaceholderText("•••• 1234 — enter to replace")).toBeInTheDocument()
  })

  it("shows account number field with 'Optional' placeholder when no last-4 exists", () => {
    const accountNoNumber: AccountResponse = { ...mockAccount, account_number_last4: null }
    renderModal(accountNoNumber)
    expect(screen.getByPlaceholderText("Optional")).toBeInTheDocument()
  })

  it("sends account_number in update payload when a value is entered", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    vi.mocked(accountsApi.update).mockResolvedValue(mockAccount)

    renderModal(mockAccount, onClose)

    const accountNumberInput = screen.getByPlaceholderText("•••• 1234 — enter to replace")
    await user.type(accountNumberInput, "9876543210")
    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ account_number: "9876543210" }),
      )
    })
  })

  it("sends account_number as null when field is left blank", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.update).mockResolvedValue(mockAccount)

    renderModal()

    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ account_number: null }),
      )
    })
  })

  it("pre-fills tax treatment from the account and sends an override on save", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    vi.mocked(accountsApi.update).mockResolvedValue(mockAccount)

    const iraAccount: AccountResponse = {
      ...mockAccount,
      account_type: "retirement_ira",
      tax_treatment: "pretax",
    }
    renderModal(iraAccount, onClose)

    const select = screen.getByLabelText("Tax treatment") as HTMLSelectElement
    expect(select.value).toBe("pretax")

    await user.selectOptions(select, "roth")
    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ tax_treatment: "roth" }),
      )
    })
  })

  it("sends tax_treatment as null when set to Not set", async () => {
    const user = userEvent.setup()
    vi.mocked(accountsApi.update).mockResolvedValue(mockAccount)

    const iraAccount: AccountResponse = { ...mockAccount, tax_treatment: "pretax" }
    renderModal(iraAccount)

    await user.selectOptions(screen.getByLabelText("Tax treatment"), "")
    await user.click(screen.getByRole("button", { name: /save/i }))

    await waitFor(() => {
      expect(accountsApi.update).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ tax_treatment: null }),
      )
    })
  })

  it("hides account number field for dependent role", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useAuth).mockImplementation((selector: any) => selector({ role: "dependent" }))
    renderModal()
    expect(screen.queryByPlaceholderText("•••• 1234 — enter to replace")).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/account number/i)).not.toBeInTheDocument()
  })
})
