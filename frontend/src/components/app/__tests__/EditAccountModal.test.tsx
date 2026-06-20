import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import EditAccountModal from "../EditAccountModal"
import { accountsApi } from "@/api/accounts"
import { ApiError } from "@/api/client"
import { createClient, wrapper } from "@/test/testUtils"
import type { AccountResponse } from "@/api/types"

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    update: vi.fn(),
  },
}))

const mockAccount: AccountResponse = {
  id: "acct-1",
  nickname: "Chase Checking",
  account_type: "checking",
  owner_member_id: "m1",
  institution_name: "Chase",
  account_number_last4: "1234",
  include_in_net_worth: true,
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
})
