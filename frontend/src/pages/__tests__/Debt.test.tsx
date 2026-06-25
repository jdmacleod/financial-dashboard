import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Debt from "@/pages/Debt"
import type { DebtPayoffComparisonResponse } from "@/api/types"

const plan = (strategy: "avalanche" | "snowball"): DebtPayoffComparisonResponse["avalanche"] => ({
  strategy,
  months_to_payoff: 310,
  total_interest_paid: "163830.82",
  payoff_date: "2052-04-25",
  monthly_series: [
    { month: 0, date: "2026-07-01", total_remaining: "342000.00", per_debt: { d1: "342000.00" } },
    { month: 1, date: "2026-08-01", total_remaining: "341000.00", per_debt: { d1: "341000.00" } },
  ],
  payoff_order: ["Mortgage"],
})

const mockResponse: DebtPayoffComparisonResponse = {
  debts: [
    {
      debt_id: "d1",
      account_id: "a1",
      nickname: "Mortgage",
      current_balance: "342000.00",
      interest_rate: "0.0325",
      minimum_payment: "1632.00",
    },
  ],
  avalanche: plan("avalanche"),
  snowball: plan("snowball"),
}

vi.mock("@/api/debt", () => ({
  debtApi: { payoffComparison: vi.fn(() => Promise.resolve(mockResponse)) },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Debt />
    </QueryClientProvider>,
  )
}

describe("Debt — extra monthly payment field", () => {
  beforeEach(() => vi.clearAllMocks())

  it("starts empty (no stuck leading 0) and is reachable by its label", async () => {
    renderPage()
    const input = screen.getByLabelText("Extra monthly payment:") as HTMLInputElement
    expect(input.value).toBe("")
    expect(input).toHaveAttribute("placeholder", "0")
  })

  it("shows exactly the typed value and refetches with the parsed number", async () => {
    const user = userEvent.setup()
    const { debtApi } = await import("@/api/debt")
    renderPage()
    const input = screen.getByLabelText("Extra monthly payment:") as HTMLInputElement
    await user.type(input, "1000")
    expect(input.value).toBe("1000") // not "01000"
    await waitFor(() => expect(debtApi.payoffComparison).toHaveBeenCalledWith(1000))
  })

  it("treats an empty field as 0 (no extra payment) and hides the applied hint", async () => {
    const { debtApi } = await import("@/api/debt")
    renderPage()
    await waitFor(() => expect(debtApi.payoffComparison).toHaveBeenCalledWith(0))
    expect(screen.queryByText(/Applied to target debt/)).not.toBeInTheDocument()
  })
})
