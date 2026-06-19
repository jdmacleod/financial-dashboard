import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import ReportNetWorth from "../ReportNetWorth"
import { reportsApi } from "@/api/reports"
import type { NetWorthReport } from "@/api/types"

vi.mock("@/api/reports", () => ({
  reportsApi: {
    netWorth: vi.fn(),
  },
}))

vi.mock("@tanstack/react-router", () => ({
  useSearch: () => ({}),
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

vi.mock("recharts", () => ({
  AreaChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="chart">{children}</div>
  ),
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

function makeBreakdown(overrides: Partial<Record<string, string>> = {}) {
  return {
    checking_savings: "10000.0000",
    investment: "20000.0000",
    retirement: "30000.0000",
    real_estate: "200000.0000",
    hsa: "5000.0000",
    other_assets: "1000.0000",
    mortgage: "-150000.0000",
    other_liabilities: "-5000.0000",
    ...overrides,
  }
}

function makeReport(current: NonNullable<NetWorthReport["current"]> | null = null): NetWorthReport {
  return {
    series: current ? [current] : [],
    current,
    pension_annotations: [],
  }
}

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderPage() {
  return render(
    <QueryClientProvider client={createClient()}>
      <ReportNetWorth />
    </QueryClientProvider>,
  )
}

describe("ReportNetWorth — breakdown panel", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders breakdown panel with all 8 labels when current data is present", async () => {
    const current = {
      date: "2025-01-31",
      total_assets: "266000.0000",
      total_liabilities: "155000.0000",
      net_worth: "111000.0000",
      breakdown: makeBreakdown(),
    }
    vi.mocked(reportsApi.netWorth).mockResolvedValue(makeReport(current))
    renderPage()
    await screen.findByText("Breakdown")
    expect(screen.getByText("Cash & Savings")).toBeInTheDocument()
    expect(screen.getByText("Investments")).toBeInTheDocument()
    expect(screen.getByText("Retirement")).toBeInTheDocument()
    expect(screen.getByText("Real Estate")).toBeInTheDocument()
    expect(screen.getByText("HSA")).toBeInTheDocument()
    expect(screen.getByText("Other Assets")).toBeInTheDocument()
    expect(screen.getByText("Mortgage")).toBeInTheDocument()
    expect(screen.getByText("Other Liabilities")).toBeInTheDocument()
  })

  it("does not render breakdown panel when current is null", async () => {
    vi.mocked(reportsApi.netWorth).mockResolvedValue(makeReport(null))
    renderPage()
    await new Promise((r) => setTimeout(r, 100))
    expect(screen.queryByText("Breakdown")).not.toBeInTheDocument()
  })

  it("does not divide by zero when total_assets and total_liabilities are 0", async () => {
    const current = {
      date: "2025-01-31",
      total_assets: "0.0000",
      total_liabilities: "0.0000",
      net_worth: "0.0000",
      breakdown: makeBreakdown({
        checking_savings: "0.0000",
        investment: "0.0000",
        retirement: "0.0000",
        real_estate: "0.0000",
        hsa: "0.0000",
        other_assets: "0.0000",
        mortgage: "0.0000",
        other_liabilities: "0.0000",
      }),
    }
    vi.mocked(reportsApi.netWorth).mockResolvedValue(makeReport(current))
    renderPage()
    await screen.findByText("Breakdown")
    // All bars should render with width 0% — no crash or NaN
    const bars = document.querySelectorAll<HTMLElement>("[style]")
    const widthBars = Array.from(bars).filter((el) => el.style.width === "0%")
    expect(widthBars.length).toBe(8)
  })
})
