import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import ReportMilestones from "../ReportMilestones"
import { reportsApi } from "@/api/reports"
import type { AgeMilestonesReport, MemberMilestones } from "@/api/types"

vi.mock("@/api/reports", () => ({
  reportsApi: {
    ageMilestones: vi.fn(),
  },
}))

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <ReportMilestones />
    </QueryClientProvider>,
  )
}

function member(overrides: Partial<MemberMilestones> = {}): MemberMilestones {
  return {
    member_id: "m1",
    display_name: "Pat Saver",
    date_of_birth: "1990-06-15",
    current_age: 36,
    milestones: [
      {
        key: "early_withdrawal",
        label: "Penalty-free withdrawals",
        age_label: "59y 6m",
        date: "2049-12-15",
        year: 2049,
        reached: false,
      },
      {
        key: "rmd",
        label: "Required minimum distributions begin",
        age_label: "75",
        date: "2065-06-15",
        year: 2065,
        reached: false,
      },
    ],
    note: null,
    ...overrides,
  }
}

function report(members: MemberMilestones[]): AgeMilestonesReport {
  return { members }
}

describe("ReportMilestones", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a member's milestones with a Next badge on the first upcoming", async () => {
    vi.mocked(reportsApi.ageMilestones).mockResolvedValue(report([member()]))
    renderPage()
    await waitFor(() => expect(screen.getByText("Pat Saver")).toBeInTheDocument())
    expect(screen.getByText("Penalty-free withdrawals")).toBeInTheDocument()
    expect(screen.getByText("Required minimum distributions begin")).toBeInTheDocument()
    expect(screen.getByText("Next")).toBeInTheDocument()
  })

  it("marks reached milestones", async () => {
    vi.mocked(reportsApi.ageMilestones).mockResolvedValue(
      report([
        member({
          current_age: 67,
          milestones: [
            {
              key: "medicare",
              label: "Medicare eligibility",
              age_label: "65",
              date: "2020-06-15",
              year: 2020,
              reached: true,
            },
          ],
        }),
      ]),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/reached/)).toBeInTheDocument())
  })

  it("shows the note when a member has no date of birth", async () => {
    vi.mocked(reportsApi.ageMilestones).mockResolvedValue(
      report([
        member({
          date_of_birth: null,
          current_age: null,
          milestones: [],
          note: "Add a date of birth to see this member's milestones.",
        }),
      ]),
    )
    renderPage()
    await waitFor(() => expect(screen.getByText(/Add a date of birth/)).toBeInTheDocument())
  })
})
