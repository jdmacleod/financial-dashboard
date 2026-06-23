import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { InvestmentPositionsPanel } from "@/components/app/InvestmentPositionsPanel"
import type { PositionsSummary } from "@/api/types"

const positions = vi.fn()
vi.mock("@/api/investmentLots", () => ({
  investmentLotsApi: { positions: () => positions() },
}))

const summary: PositionsSummary = {
  positions: [
    { ticker: "VTI", shares: "42", cost_basis: "9000.00", lot_count: 2 },
    { ticker: "BND", shares: "100", cost_basis: "1000.00", lot_count: 1 },
  ],
  holdings_mix: [
    { asset_class: "equity", cost_basis: "9000.00", percentage: 90.0 },
    { asset_class: "fixed_income", cost_basis: "1000.00", percentage: 10.0 },
  ],
  total_cost_basis: "10000.00",
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <InvestmentPositionsPanel />
    </QueryClientProvider>,
  )
}

describe("InvestmentPositionsPanel", () => {
  beforeEach(() => positions.mockReset())

  it("renders the top positions table and holdings mix legend", async () => {
    positions.mockResolvedValue(summary)
    renderPanel()

    await waitFor(() => {
      expect(screen.getByText("Top positions")).toBeInTheDocument()
    })
    expect(screen.getByText("VTI")).toBeInTheDocument()
    expect(screen.getByText("BND")).toBeInTheDocument()
    expect(screen.getByText("$9,000.00")).toBeInTheDocument()

    // Holdings mix legend with friendly labels and percentages.
    expect(screen.getByText("Equity")).toBeInTheDocument()
    expect(screen.getByText("Fixed income")).toBeInTheDocument()
    expect(screen.getByText("90.0%")).toBeInTheDocument()
    expect(screen.getByText("10.0%")).toBeInTheDocument()
  })

  it("maps unclassified lots to a friendly label", async () => {
    positions.mockResolvedValue({
      positions: [{ ticker: "MYSTERY", shares: "5", cost_basis: "500.00", lot_count: 1 }],
      holdings_mix: [{ asset_class: "unclassified", cost_basis: "500.00", percentage: 100.0 }],
      total_cost_basis: "500.00",
    } satisfies PositionsSummary)
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText("Unclassified")).toBeInTheDocument()
    })
  })

  it("renders nothing when there are no positions", async () => {
    positions.mockResolvedValue({
      positions: [],
      holdings_mix: [],
      total_cost_basis: "0",
    } satisfies PositionsSummary)
    const { container } = renderPanel()
    // Give the query a tick to resolve; panel should stay empty.
    await waitFor(() => {
      expect(container.querySelector("section")).toBeNull()
    })
  })
})
