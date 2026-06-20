import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import ReportCashFlow from "@/pages/ReportCashFlow"

const mockCashFlow = {
  series: [
    {
      period: "2026-01-01",
      income: "5500.00",
      expenses: "-3200.00",
      net: "2300.00",
      savings_rate: 41.8,
    },
    {
      period: "2026-02-01",
      income: "5500.00",
      expenses: "-2900.00",
      net: "2600.00",
      savings_rate: 47.3,
    },
  ],
  totals: {
    period: "total",
    income: "11000.00",
    expenses: "-6100.00",
    net: "4900.00",
    savings_rate: 44.5,
  },
}

const mockSpending = {
  total: "6100.00",
  categories: [
    {
      category_id: "c1",
      name: "Housing",
      amount: "2000.00",
      percentage: 32.8,
      transaction_count: 2,
      has_children: false,
    },
    {
      category_id: "c2",
      name: "Food",
      amount: "800.00",
      percentage: 13.1,
      transaction_count: 12,
      has_children: false,
    },
  ],
}

vi.mock("@/api/reports", () => ({
  reportsApi: {
    cashFlow: vi.fn(() => Promise.resolve(mockCashFlow)),
    spendingByCategory: vi.fn(() => Promise.resolve(mockSpending)),
  },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <ReportCashFlow />
    </QueryClientProvider>,
  )
}

describe("ReportCashFlow — Phase 7 redesign", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders page heading", () => {
    renderPage()
    expect(screen.getByRole("heading", { name: "Cash flow" })).toBeInTheDocument()
  })

  it("shows Total income KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Total income")).toBeInTheDocument()
    })
  })

  it("shows Total expenses KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Total expenses")).toBeInTheDocument()
    })
  })

  it("shows Net saved KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Net saved")).toBeInTheDocument()
    })
  })

  it("shows Savings rate KPI", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Savings rate")).toBeInTheDocument()
      expect(screen.getByText("44.5%")).toBeInTheDocument()
    })
  })

  it("shows total income value", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("$11,000.00").length).toBeGreaterThan(0)
    })
  })

  it("shows net saved value", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("$4,900.00").length).toBeGreaterThan(0)
    })
  })

  it("shows spending category names", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Housing")).toBeInTheDocument()
      expect(screen.getByText("Food")).toBeInTheDocument()
    })
  })

  it("shows Top spending categories section label", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Top spending categories")).toBeInTheDocument()
    })
  })

  it("shows By period table label", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("By period")).toBeInTheDocument()
    })
  })

  it("shows period rows in table", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("2026-01")).toBeInTheDocument()
      expect(screen.getByText("2026-02")).toBeInTheDocument()
    })
  })

  it("renders 6m/12m/24m period toggle buttons", () => {
    renderPage()
    expect(screen.getByRole("button", { name: "6m" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "12m" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "24m" })).toBeInTheDocument()
  })

  it("renders month/quarter group-by buttons", () => {
    renderPage()
    expect(screen.getByRole("button", { name: "month" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "quarter" })).toBeInTheDocument()
  })

  it("calls cashFlow API again when period toggle is changed", async () => {
    const user = userEvent.setup()
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await waitFor(() => screen.getByText("Total income"))
    await user.click(screen.getByRole("button", { name: "6m" }))
    expect(mock.cashFlow).toHaveBeenCalledWith(expect.any(String), expect.any(String), "month")
  })
})
