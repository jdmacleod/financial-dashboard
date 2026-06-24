import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import ReportRequiredDistributions from "../ReportRequiredDistributions"
import { reportsApi } from "@/api/reports"
import type { MemberRequiredDistribution, RequiredDistributionsReport } from "@/api/types"

vi.mock("@/api/reports", () => ({
  reportsApi: {
    requiredDistributions: vi.fn(),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ReportRequiredDistributions />
    </QueryClientProvider>,
  )
}

function member(overrides: Partial<MemberRequiredDistribution> = {}): MemberRequiredDistribution {
  return {
    member_id: "m1",
    display_name: "Pat Saver",
    date_of_birth: "1950-01-01",
    current_age: 74,
    rmd_start_age: 72,
    rmd_start_year: 2022,
    has_started: true,
    pretax_balance: "1000000.0000",
    balance_as_of: "2023-12-31",
    divisor: "25.5",
    rmd_amount: "39215.69",
    note: null,
    ...overrides,
  }
}

function report(members: MemberRequiredDistribution[]): RequiredDistributionsReport {
  return { year: 2024, members }
}

describe("ReportRequiredDistributions", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders the computed RMD for a member who has started", async () => {
    vi.mocked(reportsApi.requiredDistributions).mockResolvedValue(report([member()]))
    renderPage()
    await waitFor(() => expect(screen.getByText("Pat Saver")).toBeInTheDocument())
    expect(screen.getByText("$39,215.69")).toBeInTheDocument()
    expect(screen.getByText("$1,000,000.00")).toBeInTheDocument()
    expect(screen.getByText("25.5")).toBeInTheDocument()
  })

  it("shows the guidance note when RMDs have not started", async () => {
    vi.mocked(reportsApi.requiredDistributions).mockResolvedValue(
      report([
        member({
          has_started: false,
          rmd_amount: null,
          pretax_balance: null,
          divisor: null,
          note: "RMDs begin in 2040 (age 75).",
        }),
      ]),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/RMDs begin in 2040/)).toBeInTheDocument())
    expect(screen.queryByText("$39,215.69")).not.toBeInTheDocument()
  })

  it("renders an empty state when no pretax accounts exist", async () => {
    vi.mocked(reportsApi.requiredDistributions).mockResolvedValue(report([]))
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/No pretax retirement accounts yet/)).toBeInTheDocument(),
    )
  })
})
