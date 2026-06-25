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
  retirement_income: {
    social_security: "0.00",
    pension: "0.00",
    rmd: "0.00",
    total: "0.00",
    has_data: false,
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

const mockUseRouterState = vi.fn(() => "")
vi.mock("@tanstack/react-router", () => ({
  useRouterState: (opts: { select: (s: { location: { search: string } }) => unknown }) =>
    opts.select({ location: { search: mockUseRouterState() as string } }),
  useNavigate: () => vi.fn(),
  Link: ({ children, ...props }: { children: React.ReactNode; [key: string]: unknown }) => (
    <a {...props}>{children}</a>
  ),
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    cashFlow: vi.fn(() => Promise.resolve(mockCashFlow)),
    spendingByCategory: vi.fn(() => Promise.resolve(mockSpending)),
  },
}))

vi.mock("@/api/categories", () => ({
  categoriesApi: {
    list: vi.fn(() => Promise.resolve([])),
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
    mockUseRouterState.mockReturnValue("")
  })

  it("renders page heading", () => {
    renderPage()
    expect(screen.getByRole("heading", { name: "Cash Flow" })).toBeInTheDocument()
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
      expect(screen.getByText("Jan 2026")).toBeInTheDocument()
      expect(screen.getByText("Feb 2026")).toBeInTheDocument()
    })
  })

  it("renders month/quarter group-by buttons", () => {
    renderPage()
    expect(screen.getByRole("button", { name: "month" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "quarter" })).toBeInTheDocument()
  })

  it("does not render the old 6m/12m/24m period buttons", () => {
    renderPage()
    expect(screen.queryByRole("button", { name: "6m" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "12m" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "24m" })).not.toBeInTheDocument()
  })

  it("calls cashFlow API with quarter groupBy when group-by toggle is changed", async () => {
    const user = userEvent.setup()
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await waitFor(() => screen.getByText("Total income"))
    await user.click(screen.getByRole("button", { name: "quarter" }))
    expect(mock.cashFlow).toHaveBeenCalledWith(expect.any(String), expect.any(String), "quarter")
  })

  it("uses the URL range param to set the date range", async () => {
    mockUseRouterState.mockReturnValue("?range=1y")
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await waitFor(() => screen.getByText("Total income"))
    // With range=1y, cashFlow should be called with a from date ~365 days ago
    const [fromArg] = (mock.cashFlow as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      string,
      string,
    ]
    const fromDate = new Date(fromArg)
    const oneYearAgo = new Date()
    oneYearAgo.setDate(oneYearAgo.getDate() - 365)
    expect(Math.abs(fromDate.getTime() - oneYearAgo.getTime())).toBeLessThan(
      2 * 24 * 60 * 60 * 1000,
    )
  })

  it("hides the retirement income panel when there is no retirement income", async () => {
    renderPage()
    await waitFor(() => screen.getByText("Total income"))
    expect(screen.queryByText("Retirement income")).toBeNull()
  })

  it("shows the retirement income breakdown when the household draws benefits", async () => {
    const { reportsApi: mock } = await import("@/api/reports")
    ;(mock.cashFlow as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockCashFlow,
      retirement_income: {
        social_security: "4886.00",
        pension: "4000.00",
        rmd: "9000.00",
        total: "17886.00",
        has_data: true,
      },
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Retirement income")).toBeInTheDocument()
    })
    expect(screen.getByText("Social Security")).toBeInTheDocument()
    expect(screen.getByText("Pension")).toBeInTheDocument()
    expect(screen.getByText("RMDs")).toBeInTheDocument()
    expect(screen.getByText("$17,886.00")).toBeInTheDocument()
  })

  it("shows the federal tax estimate when present", async () => {
    const { reportsApi: mock } = await import("@/api/reports")
    ;(mock.cashFlow as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...mockCashFlow,
      retirement_income: {
        social_security: "40000.00",
        pension: "24000.00",
        rmd: "36000.00",
        total: "100000.00",
        has_data: true,
        federal_tax_estimate: {
          tax_year: 2025,
          filing_status: "married_filing_jointly",
          ordinary_income: "60000.00",
          social_security_gross: "40000.00",
          taxable_social_security: "34000.00",
          standard_deduction: "31500.00",
          taxable_income: "62500.00",
          federal_tax: "7023.00",
          after_tax_income: "92977.00",
          effective_rate: 0.0747,
          marginal_rate: 0.12,
        },
      },
    })
    renderPage()
    await waitFor(() => expect(screen.getByText("$7,023.00")).toBeInTheDocument())
    expect(screen.getByText("$92,977.00")).toBeInTheDocument()
    expect(screen.getByText(/% marginal/)).toBeInTheDocument()
    expect(screen.getByText(/federal only/)).toBeInTheDocument()
  })
})
