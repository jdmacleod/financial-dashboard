import { type ReactNode } from "react"
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Transactions from "../Transactions"
import { transactionsApi } from "@/api/transactions"
import { accountsApi } from "@/api/accounts"
import { categoriesApi } from "@/api/categories"
import type {
  AccountResponse,
  CategoryResponse,
  PaginatedTransactions,
  TransactionResponse,
} from "@/api/types"

vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({ accountId: "acct-1" }),
  Link: ({ children, to }: { children: ReactNode; to: string }) => <a href={to}>{children}</a>,
}))

vi.mock("@/api/pension", () => ({
  pensionApi: { get: vi.fn().mockRejectedValue(new Error("not found")) },
}))

vi.mock("@/api/properties", () => ({
  propertiesApi: { getByAccountId: vi.fn().mockRejectedValue(new Error("not found")) },
}))

vi.mock("@/api/transactions", () => ({
  transactionsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    bulkCategorize: vi.fn(),
  },
}))

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    get: vi.fn(),
    list: vi.fn(),
  },
}))

vi.mock("@/api/categories", () => ({
  categoriesApi: {
    list: vi.fn(),
  },
}))

vi.mock("@/components/app/ImportModal", () => ({
  ImportModal: () => <div data-testid="import-modal" />,
}))

vi.mock("@/components/app/HistoryPanel", () => ({
  HistoryPanel: () => <div data-testid="history-panel" />,
}))

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderPage(client?: QueryClient) {
  const qc = client ?? createClient()
  return render(
    <QueryClientProvider client={qc}>
      <Transactions />
    </QueryClientProvider>,
  )
}

const emptyTransactions: PaginatedTransactions = {
  items: [],
  total: 0,
  page: 1,
  page_size: 50,
}

const categories: CategoryResponse[] = []

function makeAccount(accountType: AccountResponse["account_type"]): AccountResponse {
  return {
    id: "acct-1",
    nickname: "Test Account",
    account_type: accountType,
    owner_member_id: null,
    ownership_entity_id: null,
    institution_name: null,
    account_number_last4: null,
    include_in_net_worth: true,
    is_active: true,
    current_balance: "0.00",
    balance_as_of: null,
    notes: null,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  }
}

const sampleTransaction: TransactionResponse = {
  id: "txn-99",
  account_id: "acct-1",
  real_estate_property_id: null,
  transaction_date: "2026-06-01",
  post_date: null,
  amount: "-50.00",
  payee_raw: "Coffee Shop",
  payee_normalized: "Coffee Shop",
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

describe("Transactions — empty state", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(categoriesApi.list).mockResolvedValue(categories)
    vi.mocked(transactionsApi.list).mockResolvedValue(emptyTransactions)
  })

  it("shows investment-type empty state CTA for retirement_401k", async () => {
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("retirement_401k"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/no transactions yet/i)).toBeInTheDocument()
    })
    // Two "New entry" buttons: one in the header, one in the empty state CTA
    expect(screen.getAllByRole("button", { name: /new entry/i })).toHaveLength(2)
    expect(screen.queryByText(/import a file/i)).not.toBeInTheDocument()
  })

  it("shows import+manual CTA for checking account", async () => {
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("checking"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/no transactions yet/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/import a bank export or add one manually/i)).toBeInTheDocument()
  })
})

describe("Transactions — add/edit modals", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("checking"))
    vi.mocked(categoriesApi.list).mockResolvedValue(categories)
    vi.mocked(transactionsApi.list).mockResolvedValue(emptyTransactions)
  })

  it("opens AddTransactionModal when 'New entry' header button is clicked", async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getAllByRole("button", { name: /new entry/i }))
    const [headerBtn] = screen.getAllByRole("button", { name: /new entry/i })
    await user.click(headerBtn)

    // AddTransactionModal header should appear
    await waitFor(() => {
      expect(screen.getByText("New transaction")).toBeInTheDocument()
    })
  })

  it("opens EditTransactionModal when pencil icon is clicked", async () => {
    vi.mocked(transactionsApi.list).mockResolvedValue({
      items: [sampleTransaction],
      total: 1,
      page: 1,
      page_size: 50,
    })

    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByTitle(/edit transaction/i))
    await user.click(screen.getByTitle(/edit transaction/i))

    await waitFor(() => {
      expect(screen.getByText("Edit transaction")).toBeInTheDocument()
    })
  })
})

describe("Transactions — delete confirm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("checking"))
    vi.mocked(categoriesApi.list).mockResolvedValue(categories)
    vi.mocked(transactionsApi.list).mockResolvedValue({
      items: [sampleTransaction],
      total: 1,
      page: 1,
      page_size: 50,
    })
  })

  it("opens delete confirm dialog when trash icon is clicked", async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    expect(screen.getByText("Delete transaction?")).toBeInTheDocument()
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument()
  })

  it("closes dialog without API call when Cancel is clicked", async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    const dialog = screen.getByRole("dialog")!
    await user.click(within(dialog).getByRole("button", { name: /cancel/i }))

    expect(screen.queryByText("Delete transaction?")).not.toBeInTheDocument()
    expect(transactionsApi.delete).not.toHaveBeenCalled()
  })

  it("calls transactionsApi.delete and closes dialog on confirm", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.delete).mockResolvedValue(undefined)

    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    const dialog = screen.getByRole("dialog")!
    await user.click(within(dialog).getByRole("button", { name: /^delete$/i }))

    await waitFor(() => {
      expect(transactionsApi.delete).toHaveBeenCalledWith("txn-99")
      expect(screen.queryByText("Delete transaction?")).not.toBeInTheDocument()
    })
  })

  it("shows error message when delete API call fails", async () => {
    const user = userEvent.setup()
    vi.mocked(transactionsApi.delete).mockRejectedValue(new Error("Network failure"))

    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    const dialog = screen.getByRole("dialog")!
    await user.click(within(dialog).getByRole("button", { name: /^delete$/i }))

    await waitFor(() => {
      expect(screen.getByText(/failed to delete/i)).toBeInTheDocument()
    })
  })

  it("shows payee and amount in delete confirm dialog", async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    const dialog = screen.getByRole("dialog")
    // textContent avoids span/p multiple-match and minus-sign encoding issues
    expect(dialog.textContent).toContain('"Coffee Shop"')
    expect(dialog.textContent).toMatch(/\$50\.00/)
  })

  it("pressing Escape closes delete confirm dialog", async () => {
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => screen.getByTitle(/delete transaction/i))
    await user.click(screen.getByTitle(/delete transaction/i))

    fireEvent(screen.getByRole("dialog"), new Event("cancel"))

    expect(screen.queryByText("Delete transaction?")).not.toBeInTheDocument()
    expect(transactionsApi.delete).not.toHaveBeenCalled()
  })
})

describe("Transactions — empty state — pension", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(categoriesApi.list).mockResolvedValue(categories)
    vi.mocked(transactionsApi.list).mockResolvedValue(emptyTransactions)
  })

  it("shows New entry button in header for pension accounts", async () => {
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("pension"))

    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: /new entry/i })).toHaveLength(1)
    })
  })

  it("hides Import button in header for pension accounts", async () => {
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("pension"))

    renderPage()

    // Wait for account data to load (Edit pension details link appears for pension)
    await waitFor(() => screen.getByRole("link", { name: /edit pension details/i }))
    expect(screen.queryByRole("button", { name: /import/i })).not.toBeInTheDocument()
  })

  it("shows New entry CTA (not Import) in empty state for pension accounts", async () => {
    vi.mocked(accountsApi.get).mockResolvedValue(makeAccount("pension"))

    renderPage()

    await waitFor(() => {
      expect(screen.getByText(/no transactions yet/i)).toBeInTheDocument()
    })
    expect(screen.getByText(/add your first entry/i)).toBeInTheDocument()
    expect(screen.queryByText(/import a bank export/i)).not.toBeInTheDocument()
  })
})
