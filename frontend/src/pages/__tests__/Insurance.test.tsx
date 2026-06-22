import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect } from "vitest"
import Insurance from "@/pages/Insurance"
import type { InsurancePolicyResponse } from "@/api/types"

const policies: InsurancePolicyResponse[] = [
  {
    id: "p1",
    household_id: "hh1",
    policy_type: "umbrella_liability",
    insured_member_id: null,
    owner_ownership_entity_id: null,
    coverage_amount: "10000000.0000",
    premium_amount: "2100.0000",
    premium_cadence: "annual",
    cash_value_account_id: null,
    metadata: { underlying: ["auto", "home"] },
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "p2",
    household_id: "hh1",
    policy_type: "permanent_life",
    insured_member_id: "m1",
    owner_ownership_entity_id: "e1",
    coverage_amount: "3000000.0000",
    premium_amount: "45000.0000",
    premium_cadence: "annual",
    cash_value_account_id: null,
    metadata: {},
    created_at: "2026-01-01T00:00:00Z",
  },
]

vi.mock("@/api/insurancePolicies", () => ({
  insurancePoliciesApi: { list: vi.fn(() => Promise.resolve(policies)) },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Insurance />
    </QueryClientProvider>,
  )
}

describe("Insurance", () => {
  it("renders policies and the trust-owned badge", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    expect(screen.getByText("Permanent Life")).toBeInTheDocument()
    // The ILIT-owned policy is flagged as outside the estate.
    expect(screen.getByText("Trust-owned (outside estate)")).toBeInTheDocument()
  })
})
