import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { AddTransactionModal } from "../AddTransactionModal"
import { transactionsApi } from "@/api/transactions"
import { ApiError } from "@/api/client"
import { createClient, wrapper, contributionsCategory, incomeCategory } from "@/test/testUtils"
import type { CategoryResponse, TransactionResponse } from "@/api/types"

vi.mock("@/api/transactions", () => ({
  transactionsApi: {
    create: vi.fn(),
  },
}))

const categories: CategoryResponse[] = [contributionsCategory, incomeCategory]

const mockTransaction: TransactionResponse = {
  id: "txn-1",
  account_id: "acct-1",
  real_estate_property_id: null,
  transaction_date: "2026-06-01",
  post_date: null,
  amount: "-100.00",
  payee_raw: "Test Payee",
  payee_normalized: "Test Payee",
  memo: null,
  category_id: null,
  is_transfer: false,
  transfer_pair_id: null,
  tags: [],
  source: "manual",
  import_job_id: null,
  external_id: null,
  is_reviewed: false,
  created_at: "2026-06-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
}

describe("AddTransactionModal", () => {
  const onClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders all form fields", () => {
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    expect(screen.getByLabelText(/date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/amount/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/payee/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/memo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
  })

  it("shows validation error when amount is zero", async () => {
    const user = userEvent.setup()
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/payee/i), "Some Payee")
    await user.clear(screen.getByLabelText(/amount/i))
    await user.type(screen.getByLabelText(/amount/i), "0")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(screen.getByText(/amount cannot be zero/i)).toBeInTheDocument()
    })
    expect(transactionsApi.create).not.toHaveBeenCalled()
  })

  it("shows validation error when payee is empty", async () => {
    const user = userEvent.setup()
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/amount/i), "50.00")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(screen.getByText(/payee is required/i)).toBeInTheDocument()
    })
    expect(transactionsApi.create).not.toHaveBeenCalled()
  })

  it("calls create and closes on success", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.create).mockResolvedValue(mockTransaction)

    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/amount/i), "50.00")
    await user.type(screen.getByLabelText(/payee/i), "Coffee Shop")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(transactionsApi.create).toHaveBeenCalledWith(
        "acct-1",
        expect.objectContaining({ amount: "50.00", payee_normalized: "Coffee Shop" }),
      )
      expect(onClose).toHaveBeenCalled()
    })
  })

  it("shows inline error for 403 response", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.create).mockRejectedValue(new ApiError(403, "Forbidden"))

    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/amount/i), "50.00")
    await user.type(screen.getByLabelText(/payee/i), "Coffee Shop")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(screen.getByText(/not authorized to modify this account/i)).toBeInTheDocument()
    })
    expect(onClose).not.toHaveBeenCalled()
  })

  it("pre-selects Contributions category for retirement_401k", () => {
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="retirement_401k"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    const categorySelect = screen.getByLabelText(/category/i) as HTMLSelectElement
    expect(categorySelect.value).toBe("cat-contributions")
  })

  it("pre-selects Income category for pension", () => {
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="pension"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    const categorySelect = screen.getByLabelText(/category/i) as HTMLSelectElement
    expect(categorySelect.value).toBe("cat-income")
  })

  it("leaves category blank for checking account", () => {
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    const categorySelect = screen.getByLabelText(/category/i) as HTMLSelectElement
    expect(categorySelect.value).toBe("")
  })

  it("pre-selects Contributions category for retirement_403b", () => {
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="retirement_403b"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    const categorySelect = screen.getByLabelText(/category/i) as HTMLSelectElement
    expect(categorySelect.value).toBe("cat-contributions")
  })

  it("closes without calling create when cancel is clicked", async () => {
    const user = userEvent.setup()
    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.click(screen.getByRole("button", { name: /cancel/i }))

    expect(onClose).toHaveBeenCalled()
    expect(transactionsApi.create).not.toHaveBeenCalled()
  })

  it("shows inline error for 422 response with string detail", async () => {
    const user = userEvent.setup()
    const err = new ApiError(422, "Amount must be a valid number")
    vi.mocked(transactionsApi.create).mockRejectedValue(err)

    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/amount/i), "50.00")
    await user.type(screen.getByLabelText(/payee/i), "Coffee Shop")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(screen.getByText("Amount must be a valid number")).toBeInTheDocument()
    })
  })

  it("shows generic error for non-ApiError exceptions", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.create).mockRejectedValue(new Error("Network failure"))

    render(
      <AddTransactionModal
        accountId="acct-1"
        accountType="checking"
        categories={categories}
        onClose={onClose}
      />,
      { wrapper: wrapper(createClient()) },
    )

    await user.type(screen.getByLabelText(/amount/i), "50.00")
    await user.type(screen.getByLabelText(/payee/i), "Coffee Shop")
    await user.click(screen.getByRole("button", { name: /add transaction/i }))

    await waitFor(() => {
      expect(screen.getByText(/failed to save/i)).toBeInTheDocument()
    })
  })
})
