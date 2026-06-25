import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Profile from "../Profile"
import { membersApi } from "@/api/members"
import { createClient, wrapper } from "@/test/testUtils"
import type { MemberResponse } from "@/api/types"

vi.mock("@/api/members", () => ({
  membersApi: {
    get: vi.fn(),
    update: vi.fn(),
  },
}))

vi.mock("@/hooks/useAuth", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  useAuth: vi.fn((selector: any) => selector({ memberId: "member-1" })),
}))

const member: MemberResponse = {
  id: "member-1",
  household_id: "hh1",
  display_name: "Pat Saver",
  role: "partner",
  date_of_birth: "1985-07-04",
  retirement_target_age: null,
  is_active: true,
  settings: {},
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
}

function renderPage() {
  const client = createClient()
  return render(<Profile />, { wrapper: wrapper(client) })
}

describe("Profile", () => {
  beforeEach(() => vi.clearAllMocks())

  it("pre-fills the form from the current member", async () => {
    vi.mocked(membersApi.get).mockResolvedValue(member)
    renderPage()
    await waitFor(() =>
      expect((screen.getByLabelText("Display name") as HTMLInputElement).value).toBe("Pat Saver"),
    )
    expect((screen.getByLabelText("Date of birth") as HTMLInputElement).value).toBe("1985-07-04")
    expect(screen.getByText("Partner")).toBeInTheDocument()
  })

  it("saves only the changed date of birth", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    vi.mocked(membersApi.update).mockResolvedValue({ ...member, date_of_birth: "1990-01-01" })
    renderPage()

    const dob = await screen.findByLabelText("Date of birth")
    await user.clear(dob)
    await user.type(dob, "1990-01-01")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(membersApi.update).toHaveBeenCalledWith("member-1", { date_of_birth: "1990-01-01" })
    })
    expect(await screen.findByText("Profile saved.")).toBeInTheDocument()
  })

  it("saves a target retirement age", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    vi.mocked(membersApi.update).mockResolvedValue({ ...member, retirement_target_age: 60 })
    renderPage()

    const ageInput = await screen.findByLabelText("Target retirement age")
    await user.type(ageInput, "60")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    await waitFor(() => {
      expect(membersApi.update).toHaveBeenCalledWith("member-1", { retirement_target_age: 60 })
    })
  })

  it("blocks an out-of-range retirement age", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    renderPage()

    const ageInput = await screen.findByLabelText("Target retirement age")
    await user.type(ageInput, "150")

    expect(screen.getByText(/whole age between 18 and 100/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled()
    expect(membersApi.update).not.toHaveBeenCalled()
  })

  it("disables save when there are no changes", async () => {
    vi.mocked(membersApi.get).mockResolvedValue(member)
    renderPage()
    const save = await screen.findByRole("button", { name: /save changes/i })
    expect(save).toBeDisabled()
  })

  it("blocks a future date of birth", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    renderPage()

    const dob = await screen.findByLabelText("Date of birth")
    await user.clear(dob)
    await user.type(dob, "2999-01-01")

    expect(screen.getByText(/can't be in the future/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled()
    expect(membersApi.update).not.toHaveBeenCalled()
  })

  it("shows a permission error when the server rejects the change", async () => {
    const user = userEvent.setup()
    const { ApiError } = await import("@/api/client")
    vi.mocked(membersApi.get).mockResolvedValue(member)
    vi.mocked(membersApi.update).mockRejectedValue(new ApiError(403, "forbidden"))
    renderPage()

    const name = await screen.findByLabelText("Display name")
    await user.clear(name)
    await user.type(name, "New Name")
    await user.click(screen.getByRole("button", { name: /save changes/i }))

    expect(await screen.findByText(/don't have permission/)).toBeInTheDocument()
  })
})
