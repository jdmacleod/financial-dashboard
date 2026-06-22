import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { EstateExposurePanel } from "@/components/app/EstateExposurePanel"
import type { EstateExposureReport } from "@/api/types"

const estateExposure = vi.fn()
vi.mock("@/api/reports", () => ({
  reportsApi: { estateExposure: () => estateExposure() },
}))

function report(overrides: Partial<EstateExposureReport>): EstateExposureReport {
  return {
    as_of: "2026-06-01",
    gross_taxable_estate: "0",
    excluded_from_estate: "0",
    total_net_worth: "0",
    exemption_per_person: "15000000",
    exemption_holders: 1,
    applicable_exemption: "15000000",
    taxable_overage: "0",
    estimated_federal_estate_tax: "0",
    federal_estate_tax_rate: 0.4,
    entities: [],
    ...overrides,
  }
}

function renderPanel() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <EstateExposurePanel />
    </QueryClientProvider>,
  )
}

describe("EstateExposurePanel", () => {
  beforeEach(() => estateExposure.mockReset())

  it("renders exposure stats and the entity breakdown when over the exemption", async () => {
    estateExposure.mockResolvedValue(
      report({
        gross_taxable_estate: "19000000",
        excluded_from_estate: "5000000",
        applicable_exemption: "15000000",
        taxable_overage: "4000000",
        estimated_federal_estate_tax: "1600000",
        entities: [
          {
            entity_id: null,
            entity_name: null,
            entity_type: null,
            is_in_taxable_estate: true,
            assets: "16000000",
            liabilities: "1000000",
            net_value: "15000000",
          },
          {
            entity_id: "e1",
            entity_name: "Family ILIT",
            entity_type: "ilit",
            is_in_taxable_estate: false,
            assets: "5000000",
            liabilities: "0",
            net_value: "5000000",
          },
        ],
      }),
    )
    renderPanel()
    await waitFor(() => expect(screen.getByText("Estate exposure")).toBeInTheDocument())
    expect(screen.getByText("$19,000,000.00")).toBeInTheDocument()
    expect(screen.getByText(/exceeds the applicable exemption/i)).toBeInTheDocument()
    expect(screen.getByText("Family ILIT")).toBeInTheDocument()
    expect(screen.getByText(/sheltered/i)).toBeInTheDocument()
  })

  it("self-hides when within the exemption and nothing is sheltered", async () => {
    estateExposure.mockResolvedValue(report({ gross_taxable_estate: "500000" }))
    const { container } = renderPanel()
    // Give the query a tick to resolve, then confirm nothing rendered.
    await waitFor(() => expect(estateExposure).toHaveBeenCalled())
    expect(container.querySelector("section")).toBeNull()
  })
})
