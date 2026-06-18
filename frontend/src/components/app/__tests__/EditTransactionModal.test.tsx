import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { EditTransactionModal } from "../EditTransactionModal"
import { transactionsApi } from "@/api/transactions"
import { ApiError } from "@/api/client"
import { createClient, wrapper, contributionsCategory } from "@/test/testUtils"
import type { CategoryResponse, TransactionResponse } from "@/api/types"

vi.mock("@/api/transactions", () => ({
  transactionsApi: {
    update: vi.fn(),
  },
}))

const categories: CategoryResponse[] = [contributionsCategory]

const existingTransaction: TransactionResponse = {
  id: "txn-42",
  account_id: "acct-1",
  real_estate_property_id: null,
  transaction_date: "2026-05-15",
  post_date: null,
  amount: "-250.00",
  payee_raw: "Grocery Store",
  payee_normalized: "Grocery Store",
  memo: "Weekly groceries",
  category_id: "cat-contributions",
  is_transfer: false,
  transfer_pair_id: null,
  tags: [],
  source: "manual",
  import_job_id: null,
  external_id: null,
  is_reviewed: false,
  created_at: "2026-05-15T00:00:00Z",
  updated_at: "2026-05-15T00:00:00Z",
}

describe("EditTransactionModal", () => {
  const onClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders fields pre-filled with existing transaction values", () => {
    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    expect((screen.getByLabelText(/date/i) as HTMLInputElement).value).toBe("2026-05-15")
    expect((screen.getByLabelText(/amount/i) as HTMLInputElement).value).toBe("-250.00")
    expect((screen.getByLabelText(/payee/i) as HTMLInputElement).value).toBe("Grocery Store")
    expect((screen.getByLabelText(/memo/i) as HTMLInputElement).value).toBe("Weekly groceries")
    expect((screen.getByLabelText(/category/i) as HTMLSelectElement).value).toBe(
      "cat-contributions",
    )
  })

  it("calls update with changed fields and closes on success", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.update).mockResolvedValue({
      ...existingTransaction,
      payee_normalized: "Updated Payee",
    })

    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    const payeeInput = screen.getByLabelText(/payee/i)
    await user.clear(payeeInput)
    await user.type(payeeInput, "Updated Payee")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(transactionsApi.update).toHaveBeenCalledWith(
        "txn-42",
        expect.objectContaining({ payee_normalized: "Updated Payee" }),
      )
      expect(onClose).toHaveBeenCalled()
    })
  })

  it("closes without calling update when cancel is clicked", async () => {
    const user = userEvent.setup()
    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.click(screen.getByRole("button", { name: /cancel/i }))

    expect(onClose).toHaveBeenCalled()
    expect(transactionsApi.update).not.toHaveBeenCalled()
  })

  it("shows inline error for 403 response", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.update).mockRejectedValue(new ApiError(403, "Forbidden"))

    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(screen.getByText(/not authorized to modify this account/i)).toBeInTheDocument()
    })
    expect(onClose).not.toHaveBeenCalled()
  })

  it("shows 'Transaction no longer exists' for 404 response", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.update).mockRejectedValue(new ApiError(404, "Not found"))

    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(screen.getByText(/transaction no longer exists/i)).toBeInTheDocument()
    })
  })

  it("uses payee_raw fallback when payee_normalized is null", () => {
    const txnWithNullNormalized: TransactionResponse = {
      ...existingTransaction,
      payee_normalized: null,
      payee_raw: "Raw Payee Name",
    }

    render(
      <EditTransactionModal
        transaction={txnWithNullNormalized}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    expect((screen.getByLabelText(/payee/i) as HTMLInputElement).value).toBe("Raw Payee Name")
  })

  it("shows generic error for non-ApiError exceptions", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.update).mockRejectedValue(new Error("Network timeout"))

    render(
      <EditTransactionModal
        transaction={existingTransaction}
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(screen.getByText(/failed to save/i)).toBeInTheDocument()
    })
  })
})
