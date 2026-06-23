import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Insurance from "@/pages/Insurance"
import type { InsurancePolicyResponse, MemberResponse, OwnershipEntityResponse } from "@/api/types"

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
    carrier: "Chubb",
    policy_number: "CHB-UMB-9921037",
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
    carrier: "Northwestern Mutual",
    policy_number: "NM-WL-2006-4412198",
    metadata: {},
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "p3",
    household_id: "hh1",
    policy_type: "disability",
    insured_member_id: "m1",
    owner_ownership_entity_id: null,
    coverage_amount: "72000.0000",
    premium_amount: "142.0000",
    premium_cadence: "monthly",
    cash_value_account_id: null,
    carrier: "Guardian",
    policy_number: "GDI-0089-4412",
    metadata: { benefit_period: "to_age_65", elimination_days: 90 },
    created_at: "2026-01-01T00:00:00Z",
  },
]

const members: MemberResponse[] = [
  {
    id: "m1",
    household_id: "hh1",
    display_name: "Wei Chen",
    role: "primary",
    date_of_birth: "1982-04-15",
    is_active: true,
    settings: {},
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
]

const entities: OwnershipEntityResponse[] = [
  {
    id: "e1",
    household_id: "hh1",
    entity_type: "irrevocable_trust",
    name: "Chen Family ILIT",
    grantor_member_id: "m1",
    is_in_taxable_estate: false,
    counts_in_personal_net_worth: false,
    created_at: "2026-01-01T00:00:00Z",
  },
]

vi.mock("@/api/insurancePolicies", () => ({
  insurancePoliciesApi: {
    list: vi.fn(() => Promise.resolve(policies)),
    create: vi.fn(() => Promise.resolve(policies[0])),
    update: vi.fn(() => Promise.resolve(policies[0])),
    delete: vi.fn(() => Promise.resolve()),
  },
}))

vi.mock("@/api/members", () => ({
  membersApi: { list: vi.fn(() => Promise.resolve(members)) },
}))

vi.mock("@/api/ownershipEntities", () => ({
  ownershipEntitiesApi: { list: vi.fn(() => Promise.resolve(entities)) },
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

describe("Insurance page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders all policy types", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    expect(screen.getByText("Permanent Life")).toBeInTheDocument()
    expect(screen.getByText("Disability")).toBeInTheDocument()
  })

  it("shows Add policy button in the header", async () => {
    renderPage()
    expect(screen.getByRole("button", { name: "Add policy" })).toBeInTheDocument()
  })

  it("shows Edit and Delete buttons for each policy", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    const editButtons = screen.getAllByRole("button", { name: "Edit" })
    const deleteButtons = screen.getAllByRole("button", { name: "Delete" })
    expect(editButtons).toHaveLength(3)
    expect(deleteButtons).toHaveLength(3)
  })

  it("shows sort control when policies are loaded", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    expect(screen.getByRole("combobox", { name: "Sort policies" })).toBeInTheDocument()
  })

  it("displays insured member name for policies with insured_member_id", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    // Two policies have insured_member_id = m1 → "Wei Chen"
    const insuredLabels = screen.getAllByText(/Insured: Wei Chen/)
    expect(insuredLabels.length).toBeGreaterThanOrEqual(1)
  })

  it("displays entity name for trust-owned policies", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Permanent Life")).toBeInTheDocument())
    expect(screen.getByText(/Chen Family ILIT \(outside estate\)/)).toBeInTheDocument()
  })

  it("opens the Add Policy modal when button is clicked", async () => {
    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Add policy" }))
    expect(screen.getByRole("heading", { name: "Add Policy" })).toBeInTheDocument()
  })

  it("closes the Add Policy modal on ✕ click", async () => {
    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Add policy" }))
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Add Policy" })).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole("button", { name: "✕" }))
    expect(screen.queryByRole("heading", { name: "Add Policy" })).not.toBeInTheDocument()
  })

  it("opens Edit modal with correct policy type pre-selected", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    const editButtons = screen.getAllByRole("button", { name: "Edit" })
    fireEvent.click(editButtons[0])
    expect(screen.getByRole("heading", { name: "Edit Policy" })).toBeInTheDocument()
    // With default type_asc sort, first card is Disability (D < P < U)
    expect(screen.getByText("Disability", { selector: "p" })).toBeInTheDocument()
  })

  it("closes Edit modal on Cancel", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    const editButtons = screen.getAllByRole("button", { name: "Edit" })
    fireEvent.click(editButtons[0])
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(screen.queryByRole("heading", { name: "Edit Policy" })).not.toBeInTheDocument()
  })

  it("displays carrier name on policy cards", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    expect(screen.getByText("Chubb")).toBeInTheDocument()
    expect(screen.getByText("Guardian")).toBeInTheDocument()
  })

  it("displays policy number alongside carrier on cards", async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText("Umbrella Liability")).toBeInTheDocument())
    expect(screen.getByText(/#CHB-UMB-9921037/)).toBeInTheDocument()
  })

  it("shows the empty-state Add button when no policies exist", async () => {
    const { insurancePoliciesApi } = await import("@/api/insurancePolicies")
    vi.mocked(insurancePoliciesApi.list).mockResolvedValueOnce([])

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(
      <QueryClientProvider client={qc}>
        <Insurance />
      </QueryClientProvider>,
    )
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Add first policy" })).toBeInTheDocument(),
    )
  })
})
