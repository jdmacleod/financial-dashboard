import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { ApiError } from "@/api/client"
import { membersApi } from "@/api/members"
import { provisioningApi } from "@/api/provisioning"
import type { MemberResponse } from "@/api/types"

vi.mock("@/api/members", () => ({
  membersApi: {
    list: vi.fn(),
    update: vi.fn(),
    create: vi.fn(),
  },
}))

vi.mock("@/api/provisioning", () => ({
  provisioningApi: {
    provision: vi.fn(),
    regenerateTemporaryPassword: vi.fn(),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn((selector: (s: { role: string; memberId: string }) => unknown) =>
    selector({ role: "primary", memberId: "member-1" }),
  ),
}))

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderWithClient(ui: React.ReactElement, client?: QueryClient) {
  const qc = client ?? createClient()
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

const partnerMember: MemberResponse = {
  id: "member-2",
  household_id: "hh-1",
  display_name: "Sam Smith",
  role: "partner",
  date_of_birth: null,
  is_active: true,
  settings: {},
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
}

// We test the MemberSlideOver and AddMemberModal components by importing them
// from the Members page module. Since they're not exported, we render Members
// and interact with its child modals.
describe("Members page — MemberSlideOver", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(membersApi.list).mockResolvedValue([partnerMember])
    vi.mocked(membersApi.update).mockResolvedValue({ ...partnerMember })
  })

  async function openSlideOver() {
    const Members = (await import("../Members")).default
    renderWithClient(<Members />)
    await waitFor(() => screen.getByText("Sam Smith"))
    await userEvent.click(screen.getByText("Sam Smith"))
  }

  it("shows role select when viewer is primary", async () => {
    await openSlideOver()
    expect(screen.getByRole("combobox")).toBeInTheDocument()
    // select should contain all three role options
    expect(screen.getByRole("option", { name: "Primary" })).toBeInTheDocument()
    expect(screen.getByRole("option", { name: "Partner" })).toBeInTheDocument()
    expect(screen.getByRole("option", { name: "Dependent" })).toBeInTheDocument()
  })

  it("Save button is disabled when no changes have been made", async () => {
    await openSlideOver()
    const saveBtn = screen.getByRole("button", { name: /^Save$/i })
    expect(saveBtn).toBeDisabled()
  })

  it("two-step promotion: first click shows confirm banner, not mutation", async () => {
    await openSlideOver()
    await userEvent.selectOptions(screen.getByRole("combobox"), "primary")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    expect(screen.getByText(/Grant primary access/i)).toBeInTheDocument()
    expect(membersApi.update).not.toHaveBeenCalled()
  })

  it("two-step promotion: second click fires mutation", async () => {
    await openSlideOver()
    await userEvent.selectOptions(screen.getByRole("combobox"), "primary")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    await userEvent.click(screen.getByRole("button", { name: /Confirm & Save/i }))
    await waitFor(() =>
      expect(membersApi.update).toHaveBeenCalledWith("member-2", { role: "primary" }),
    )
  })

  it("shows 409 error message without confirmPromotion banner", async () => {
    vi.mocked(membersApi.update).mockRejectedValue(new ApiError(409, "at least one primary"))
    await openSlideOver()
    await userEvent.selectOptions(screen.getByRole("combobox"), "primary")
    // first click → confirmPromotion
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    // second click → fires mutation → rejects with 409
    await userEvent.click(screen.getByRole("button", { name: /Confirm & Save/i }))
    await waitFor(() =>
      expect(screen.getByText(/at least one primary member must remain/i)).toBeInTheDocument(),
    )
    expect(screen.queryByText(/Grant primary access/i)).not.toBeInTheDocument()
  })

  it("shows generic error for non-409 mutations", async () => {
    vi.mocked(membersApi.update).mockRejectedValue(new Error("Network error"))
    await openSlideOver()
    // make a name change so Save is enabled
    const nameInput = screen.getByDisplayValue("Sam Smith")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Sam Updated")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/i }))
    await waitFor(() => expect(screen.getByText(/Failed to update member/i)).toBeInTheDocument())
  })
})

describe("Members page — AddPersonSlideOver (provisioning)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(membersApi.list).mockResolvedValue([partnerMember])
  })

  async function openAddPerson() {
    const Members = (await import("../Members")).default
    renderWithClient(<Members />)
    await waitFor(() => screen.getByRole("button", { name: /Add person/i }))
    await userEvent.click(screen.getByRole("button", { name: /Add person/i }))
  }

  it("reveals the one-time temporary password on success", async () => {
    vi.mocked(provisioningApi.provision).mockResolvedValue({
      member: { ...partnerMember, id: "member-3", display_name: "Newbie" },
      user: {
        id: "user-3",
        member_id: "member-3",
        email: "newbie@example.com",
        is_active: true,
        last_login: null,
        created_at: "2025-01-01T00:00:00Z",
      },
      temporary_password: "Temp-Pass-XYZ123", // pragma: allowlist secret — test fixture
    })
    await openAddPerson()
    const dialog = screen.getByRole("dialog")
    await userEvent.type(within(dialog).getByLabelText(/Display name/i), "Newbie")
    await userEvent.type(within(dialog).getByLabelText(/Email/i), "newbie@example.com")
    await userEvent.click(within(dialog).getByRole("button", { name: /^Add person$/i }))

    await waitFor(() => expect(screen.getByText("Person added")).toBeInTheDocument())
    expect(screen.getByDisplayValue("Temp-Pass-XYZ123")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Copy password/i })).toBeInTheDocument()
    expect(screen.getByText(/shown once/i)).toBeInTheDocument()
  })

  it("shows an inline error when the email is already in use (409)", async () => {
    vi.mocked(provisioningApi.provision).mockRejectedValue(new ApiError(409, "dup"))
    await openAddPerson()
    const dialog = screen.getByRole("dialog")
    await userEvent.type(within(dialog).getByLabelText(/Display name/i), "Dupe")
    await userEvent.type(within(dialog).getByLabelText(/Email/i), "primary@example.com")
    await userEvent.click(within(dialog).getByRole("button", { name: /^Add person$/i }))
    await waitFor(() => expect(screen.getByText(/already has a login/i)).toBeInTheDocument())
    expect(provisioningApi.provision).toHaveBeenCalled()
  })
})
