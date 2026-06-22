import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect } from "vitest"
import Insights from "@/pages/Insights"
import type { AdvisoryNoteResponse } from "@/api/types"

const notes: AdvisoryNoteResponse[] = [
  {
    id: "n1",
    household_id: "hh1",
    account_id: null,
    ownership_entity_id: null,
    category: "estate",
    title: "New York estate cliff",
    body: "State estate exposure once over 105% of the exemption.",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "n2",
    household_id: "hh1",
    account_id: "a1",
    ownership_entity_id: null,
    category: "concentration",
    title: "Single-stock position",
    body: "Roughly 30% of the portfolio in one ticker.",
    created_at: "2026-02-01T00:00:00Z",
  },
]

vi.mock("@/api/advisoryNotes", () => ({
  advisoryNotesApi: {
    list: vi.fn(() => Promise.resolve(notes)),
  },
}))

// The Insights page also renders the estate-exposure panel; stub the report so
// it self-hides (no overage, nothing sheltered) and stays out of these assertions.
vi.mock("@/api/reports", () => ({
  reportsApi: {
    estateExposure: vi.fn(() =>
      Promise.resolve({
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
      }),
    ),
  },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Insights />
    </QueryClientProvider>,
  )
}

describe("Insights", () => {
  it("renders advisory notes grouped by category", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("New York estate cliff")).toBeInTheDocument())
    expect(screen.getByText("Single-stock position")).toBeInTheDocument()
    // Category labels appear in both the filter chips and the section headings.
    expect(screen.getAllByText("Estate").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Concentration").length).toBeGreaterThan(0)
  })

  it("filters notes when a category chip is selected", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("New York estate cliff")).toBeInTheDocument())
    // Click the Estate filter chip (button) → only the estate note remains.
    const estateChip = screen.getAllByText("Estate").find((el) => el.closest("button"))!
    fireEvent.click(estateChip.closest("button")!)
    expect(screen.getByText("New York estate cliff")).toBeInTheDocument()
    expect(screen.queryByText("Single-stock position")).not.toBeInTheDocument()
  })

  it("shows an empty state when there are no notes", async () => {
    const { advisoryNotesApi } = await import("@/api/advisoryNotes")
    vi.mocked(advisoryNotesApi.list).mockResolvedValueOnce([])
    renderPage()
    await waitFor(() => expect(screen.getByText("No advisory notes yet.")).toBeInTheDocument())
  })
})
