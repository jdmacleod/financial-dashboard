import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect } from "vitest"
import Estate from "@/pages/Estate"
import type { AdvisoryNoteResponse, OwnershipEntityResponse } from "@/api/types"

const ilit: OwnershipEntityResponse = {
  id: "e1",
  household_id: "hh1",
  entity_type: "ilit",
  name: "Castellano ILIT",
  grantor_member_id: "m1",
  is_in_taxable_estate: false,
  counts_in_personal_net_worth: false,
  created_at: "2026-01-01T00:00:00Z",
}

const note: AdvisoryNoteResponse = {
  id: "n1",
  household_id: "hh1",
  account_id: null,
  ownership_entity_id: "e1",
  category: "estate",
  title: "ILIT keeps the death benefit out of the estate",
  body: "Premiums funded by annual Crummey gifts.",
  created_at: "2026-01-01T00:00:00Z",
}

vi.mock("@/api/ownershipEntities", () => ({
  ownershipEntitiesApi: { list: vi.fn(() => Promise.resolve([ilit])) },
}))

vi.mock("@/api/advisoryNotes", () => ({
  advisoryNotesApi: { list: vi.fn(() => Promise.resolve([note])) },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Estate />
    </QueryClientProvider>,
  )
}

describe("Estate", () => {
  it("renders an entity with plain-language flags and its anchored note", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Castellano ILIT")).toBeInTheDocument())
    expect(screen.getByText("ILIT")).toBeInTheDocument()
    expect(screen.getByText("Excluded from net worth")).toBeInTheDocument()
    expect(screen.getByText("Outside taxable estate")).toBeInTheDocument()
    // Entity-anchored advisory note surfaced via AdvisoryNotesPanel.
    await waitFor(() =>
      expect(
        screen.getByText("ILIT keeps the death benefit out of the estate"),
      ).toBeInTheDocument(),
    )
  })
})
