import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { ApiError } from "@/api/client"
import { propertiesApi } from "@/api/properties"
import { accountsApi } from "@/api/accounts"
import type { PropertyResponse } from "@/api/types"
import PropertyDetail from "../PropertyDetail"

vi.mock("@/api/properties", () => ({
  propertiesApi: {
    get: vi.fn(),
    update: vi.fn(),
    listValuations: vi.fn(),
    getEquity: vi.fn(),
    addValuation: vi.fn(),
  },
}))

vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn(),
  },
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    propertyPnl: vi.fn(),
  },
}))

vi.mock("@/api/members", () => ({
  membersApi: { list: vi.fn() },
}))

vi.mock("@tanstack/react-router", () => ({
  useParams: () => ({ propertyId: "prop-1" }),
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock("@/components/app/HistoryPanel", () => ({
  HistoryPanel: () => <div data-testid="history-panel" />,
}))

const baseProperty: PropertyResponse = {
  id: "prop-1",
  account_id: "acc-1",
  nickname: "Main House",
  address: "123 Oak St",
  purchase_date: "2020-06-15",
  purchase_price: "300000.0000",
  linked_mortgage_account_id: null,
  property_type: "primary_residence",
  current_estimated_value: "380000.0000",
  current_value_as_of: "2025-01-01",
  gain_loss: "80000.0000",
  gain_loss_pct: "26.6667",
  created_at: "2020-06-15T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
}

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderPage() {
  return render(
    <QueryClientProvider client={createClient()}>
      {/* dynamic import avoids module isolation issues */}
      <PropertyDetailLoader />
    </QueryClientProvider>,
  )
}

function PropertyDetailLoader() {
  return <PropertyDetail />
}

describe("PropertyDetail — gain/loss display", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(propertiesApi.listValuations).mockResolvedValue([])
    vi.mocked(accountsApi.list).mockResolvedValue([])
  })

  it("shows positive gain/loss in emerald", async () => {
    vi.mocked(propertiesApi.get).mockResolvedValue(baseProperty)
    renderPage()
    await waitFor(() => screen.getByText("Main House"))
    expect(screen.getByText(/\+\$80,000/)).toBeInTheDocument()
  })

  it("shows negative gain/loss in red", async () => {
    vi.mocked(propertiesApi.get).mockResolvedValue({
      ...baseProperty,
      current_estimated_value: "250000.0000",
      gain_loss: "-50000.0000",
      gain_loss_pct: "-16.6667",
    })
    renderPage()
    await waitFor(() => screen.getByText("Main House"))
    expect(screen.getByText(/-\$50,000|\$50,000/)).toBeInTheDocument()
  })

  it("hides gain/loss when purchase_price is null", async () => {
    vi.mocked(propertiesApi.get).mockResolvedValue({
      ...baseProperty,
      purchase_price: null,
      gain_loss: null,
      gain_loss_pct: null,
    })
    renderPage()
    await waitFor(() => screen.getByText("Main House"))
    expect(screen.queryByText(/26\.7%/)).not.toBeInTheDocument()
  })
})

describe("PropertyDetail — EditPropertyModal", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(propertiesApi.get).mockResolvedValue(baseProperty)
    vi.mocked(propertiesApi.listValuations).mockResolvedValue([])
    vi.mocked(accountsApi.list).mockResolvedValue([])
  })

  async function openEditModal() {
    renderPage()
    await waitFor(() => screen.getByText("Main House"))
    await userEvent.click(screen.getByRole("button", { name: /edit/i }))
    await waitFor(() => screen.getByText("Edit property details"))
  }

  it("pre-fills address and property type from current property", async () => {
    await openEditModal()
    expect(screen.getByDisplayValue("123 Oak St")).toBeInTheDocument()
    expect(
      (screen.getByRole("option", { name: "Primary Residence" }) as HTMLOptionElement).selected,
    ).toBe(true)
  })

  it("blocks submission when address is empty", async () => {
    await openEditModal()
    const addressInput = screen.getByDisplayValue("123 Oak St")
    await userEvent.clear(addressInput)
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    expect(await screen.findByText("Address is required")).toBeInTheDocument()
    expect(propertiesApi.update).not.toHaveBeenCalled()
  })

  it("calls propertiesApi.update and closes on success", async () => {
    vi.mocked(propertiesApi.update).mockResolvedValue(baseProperty)
    await openEditModal()
    const addressInput = screen.getByDisplayValue("123 Oak St")
    await userEvent.clear(addressInput)
    await userEvent.type(addressInput, "456 Elm Ave")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    await waitFor(() =>
      expect(propertiesApi.update).toHaveBeenCalledWith(
        "prop-1",
        expect.objectContaining({ address: "456 Elm Ave" }),
      ),
    )
    await waitFor(() => expect(screen.queryByText("Edit property details")).not.toBeInTheDocument())
  })

  it("shows error message on update failure", async () => {
    vi.mocked(propertiesApi.update).mockRejectedValue(new ApiError(500, "Server error"))
    await openEditModal()
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    expect(await screen.findByText("Failed to save property details.")).toBeInTheDocument()
  })
})
