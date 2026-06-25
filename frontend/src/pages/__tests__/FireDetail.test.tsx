import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import FireDetail from "../FireDetail"
import { fireApi } from "@/api/fire"
import type { FireScenarioResponse, RothLadderResponse } from "@/api/types"

vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({ scenarioId: "s1" }),
  useNavigate: () => vi.fn(),
}))

vi.mock("@/api/fire", () => ({
  fireApi: {
    get: vi.fn(),
    projection: vi.fn(),
    rothLadder: vi.fn(),
    detect: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}))

const scenario: FireScenarioResponse = {
  id: "s1",
  household_id: "h1",
  member_id: null,
  name: "Primary",
  target_annual_spend: "60000.00",
  safe_withdrawal_rate: "0.04",
  expected_annual_return: "0.07",
  expected_inflation_rate: "0.03",
  target_retirement_age: 62,
  additional_income_streams: [],
  detected_annual_income: null,
  detected_annual_expenses: null,
  detected_savings_rate: null,
  detected_portfolio_value: null,
  detection_trailing_months: 12,
  detected_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
}

const availableLadder: RothLadderResponse = {
  available: true,
  note: null,
  ceiling_rate: "0.12",
  gap_start_year: 2032,
  gap_start_age: 62,
  rmd_start_age: 75,
  horizon_age: 90,
  total_converted: "864500.00",
  lifetime_tax_with: "120000.00",
  lifetime_tax_without: "176000.00",
  lifetime_tax_saved: "56000.00",
  years: [
    {
      year: 2032,
      age: 62,
      pretax_balance: "933500.00",
      ordinary_income: "0.00",
      social_security: "0.00",
      conversion: "66500.00",
      federal_tax: "5800.00",
    },
  ],
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  vi.mocked(fireApi.get).mockResolvedValue(scenario)
  vi.mocked(fireApi.projection).mockResolvedValue({
    summary: {
      fire_year: null,
      fire_age: null,
      years_to_fire: null,
      fire_number: "1500000.00",
      headline: "FIRE number not reached within 75 years",
    },
    projections: [],
  })
  return render(
    <QueryClientProvider client={qc}>
      <FireDetail />
    </QueryClientProvider>,
  )
}

describe("FireDetail — Roth conversion ladder", () => {
  beforeEach(() => vi.clearAllMocks())

  it("shows the lifetime-tax-saved headline and a conversion row", async () => {
    vi.mocked(fireApi.rothLadder).mockResolvedValue(availableLadder)
    renderPage()
    await waitFor(() => expect(screen.getByText("Roth conversion ladder")).toBeInTheDocument())
    expect(screen.getByText(/saves about/)).toBeInTheDocument()
    expect(screen.getByText("$56,000.00")).toBeInTheDocument()
    // Conversion row.
    expect(screen.getByText("$66,500.00")).toBeInTheDocument()
  })

  it("frames a negative saving as a cost", async () => {
    vi.mocked(fireApi.rothLadder).mockResolvedValue({
      ...availableLadder,
      lifetime_tax_with: "176000.00",
      lifetime_tax_without: "120000.00",
      lifetime_tax_saved: "-56000.00",
    })
    renderPage()
    await waitFor(() => expect(screen.getByText(/costs about/)).toBeInTheDocument())
    expect(screen.getByText("$56,000.00")).toBeInTheDocument()
  })

  it("shows the note when the ladder is unavailable", async () => {
    vi.mocked(fireApi.rothLadder).mockResolvedValue({
      ...availableLadder,
      available: false,
      note: "Set the household filing status to model conversions.",
      years: [],
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Set the household filing status/)).toBeInTheDocument(),
    )
  })

  it("refetches with the chosen target bracket", async () => {
    vi.mocked(fireApi.rothLadder).mockResolvedValue(availableLadder)
    renderPage()
    await waitFor(() => expect(screen.getByText("Roth conversion ladder")).toBeInTheDocument())
    await userEvent.selectOptions(screen.getByLabelText("Conversion target bracket"), "0.22")
    await waitFor(() =>
      expect(fireApi.rothLadder).toHaveBeenCalledWith("s1", { ceiling_rate: "0.22" }),
    )
  })
})
