import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import SettingsHousehold from "../SettingsHousehold"
import { householdApi } from "@/api/household"
import { createClient, wrapper } from "@/test/testUtils"
import type { HouseholdResponse } from "@/api/types"

vi.mock("@/api/household", () => ({
  householdApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

let mockRole = "primary"
vi.mock("@/hooks/useAuth", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuth: vi.fn((selector: any) => selector({ role: mockRole })),
}))

const household: HouseholdResponse = {
  id: "hh-1",
  name: "Test Household",
  settings: {},
  filing_status: "married_filing_jointly",
  state: "NY",
  created_at: "2025-01-01T00:00:00Z",
}

function renderPage() {
  const client = createClient()
  return render(<SettingsHousehold />, { wrapper: wrapper(client) })
}

describe("SettingsHousehold", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockRole = "primary"
  })

  it("pre-fills filing status and state from the household", async () => {
    vi.mocked(householdApi.get).mockResolvedValue(household)
    renderPage()

    await waitFor(() =>
      expect((screen.getByLabelText("Filing status") as HTMLSelectElement).value).toBe(
        "married_filing_jointly",
      ),
    )
    expect((screen.getByLabelText("State of residence") as HTMLSelectElement).value).toBe("NY")
  })

  it("saves changed filing status and state", async () => {
    const user = userEvent.setup()
    vi.mocked(householdApi.get).mockResolvedValue(household)
    vi.mocked(householdApi.update).mockResolvedValue({
      ...household,
      filing_status: "single",
      state: "CA",
    })
    renderPage()

    const filing = await screen.findByLabelText("Filing status")
    await user.selectOptions(filing, "single")
    await user.selectOptions(screen.getByLabelText("State of residence"), "CA")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(householdApi.update).toHaveBeenCalledWith({ filing_status: "single", state: "CA" })
    })
    expect(await screen.findByText(/saved/i)).toBeInTheDocument()
  })

  it("sends nulls when clearing both fields", async () => {
    const user = userEvent.setup()
    vi.mocked(householdApi.get).mockResolvedValue(household)
    vi.mocked(householdApi.update).mockResolvedValue({
      ...household,
      filing_status: null,
      state: null,
    })
    renderPage()

    const filing = await screen.findByLabelText("Filing status")
    await user.selectOptions(filing, "")
    await user.selectOptions(screen.getByLabelText("State of residence"), "")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(householdApi.update).toHaveBeenCalledWith({ filing_status: null, state: null })
    })
  })

  it("disables save when there are no changes", async () => {
    vi.mocked(householdApi.get).mockResolvedValue(household)
    renderPage()
    const save = await screen.findByRole("button", { name: /save changes/i })
    expect(save).toBeDisabled()
  })

  it("shows a read-only view for a non-primary member", async () => {
    mockRole = "partner"
    vi.mocked(householdApi.get).mockResolvedValue(household)
    renderPage()

    await waitFor(() =>
      expect(screen.getByText(/Only a primary member can change/i)).toBeInTheDocument(),
    )
    expect(screen.queryByRole("button", { name: /save changes/i })).not.toBeInTheDocument()
    expect(screen.getByText("Married filing jointly")).toBeInTheDocument()
  })
})
