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
    socialSecurityEstimate: vi.fn(),
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
  ss_monthly_benefit_at_fra: null,
  ss_claiming_age: null,
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

  it("shows the Social Security claiming table after entering a benefit", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    vi.mocked(membersApi.socialSecurityEstimate).mockResolvedValue({
      pia_monthly: "2000.00",
      fra_months: 804,
      options: [
        {
          claiming_age: 62,
          monthly_benefit: "1400.00",
          annual_benefit: "16800.00",
          pct_of_pia: 70,
          is_fra: false,
        },
        {
          claiming_age: 67,
          monthly_benefit: "2000.00",
          annual_benefit: "24000.00",
          pct_of_pia: 100,
          is_fra: true,
        },
        {
          claiming_age: 70,
          monthly_benefit: "2480.00",
          annual_benefit: "29760.00",
          pct_of_pia: 124,
          is_fra: false,
        },
      ],
    })
    renderPage()

    const input = await screen.findByLabelText("Monthly benefit at FRA")
    await user.type(input, "2000")

    await waitFor(() => expect(screen.getByText("$1,400.00")).toBeInTheDocument())
    expect(screen.getByText("$2,480.00")).toBeInTheDocument()
    expect(screen.getByText("FRA")).toBeInTheDocument()
    expect(membersApi.socialSecurityEstimate).toHaveBeenCalledWith("member-1", "2000")
  })

  it("saves the SS benefit estimate and claiming age", async () => {
    const user = userEvent.setup()
    vi.mocked(membersApi.get).mockResolvedValue(member)
    vi.mocked(membersApi.update).mockResolvedValue({
      ...member,
      ss_monthly_benefit_at_fra: "2000",
      ss_claiming_age: 70,
    })
    renderPage()

    const input = await screen.findByLabelText("Monthly benefit at FRA")
    await user.type(input, "2000")
    await user.selectOptions(screen.getByLabelText("Planned claiming age"), "70")
    await user.click(screen.getByRole("button", { name: /^save$/i }))

    await waitFor(() => {
      expect(membersApi.update).toHaveBeenCalledWith("member-1", {
        ss_monthly_benefit_at_fra: "2000",
        ss_claiming_age: 70,
      })
    })
  })

  it("prompts for date of birth when the member has none", async () => {
    vi.mocked(membersApi.get).mockResolvedValue({ ...member, date_of_birth: null })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText(/Add your date of birth above to estimate/)).toBeInTheDocument(),
    )
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
