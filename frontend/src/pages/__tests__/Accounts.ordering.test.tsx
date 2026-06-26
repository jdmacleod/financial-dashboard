import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Accounts from "@/pages/Accounts"

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, ...props }: React.PropsWithChildren<{ to: string; params?: unknown }>) => (
    <a href={String(props.to)}>{children}</a>
  ),
  useNavigate: () => vi.fn(),
  useRouterState: (opts: { select: (s: { location: { search: string } }) => unknown }) =>
    opts.select({ location: { search: "" } }),
}))

vi.mock("@/hooks/useAuth", () => ({
  useAuth: (selector: (s: { role: string; memberId: string }) => unknown) =>
    selector({ role: "primary", memberId: "m1" }),
}))

vi.mock("@/api/snapshots", () => ({
  snapshotsApi: { list: vi.fn(() => Promise.resolve([])) },
}))

vi.mock("@/components/app/AddAccountModal", () => ({ default: () => null }))
vi.mock("@/components/app/ArchiveAccountModal", () => ({ default: () => null }))
vi.mock("@/components/app/EditAccountModal", () => ({ default: () => null }))

const listMock = vi.fn()
vi.mock("@/api/accounts", () => ({
  accountsApi: { list: () => listMock(), update: vi.fn(() => Promise.resolve({})) },
}))

function acct(id: string, nickname: string, account_type: string, balance: string) {
  return {
    id,
    nickname,
    account_type,
    owner_member_id: "m1",
    institution_name: "Inst",
    account_number_last4: "0000",
    include_in_net_worth: true,
    is_active: true,
    current_balance: balance,
    balance_as_of: "2026-06-01",
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
  }
}

// Intentionally supplied in a jumbled order to prove the page re-sorts.
const accounts = [
  acct("a1", "Alpha Checking", "checking", "1000.00"),
  acct("a2", "Zulu Savings", "savings", "9000.00"),
  acct("a3", "Brokerage One", "investment_brokerage", "5000.00"),
  acct("a4", "Big 401k", "retirement_401k", "50000.00"),
  acct("a5", "Small Card", "credit_card", "-500.00"),
  acct("a6", "Big Mortgage", "mortgage", "-200000.00"),
]

function renderAccounts() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Accounts />
    </QueryClientProvider>,
  )
}

function order(text: string, ...needles: string[]): number[] {
  return needles.map((n) => text.indexOf(n))
}

describe("Accounts — group order + within-group sort", () => {
  beforeEach(() => {
    localStorage.clear()
    listMock.mockReset()
    listMock.mockResolvedValue(accounts)
  })

  it("renders groups in the canonical order (Investments before Retirement, matching the sidebar)", async () => {
    const { container } = renderAccounts()
    await screen.findByText("Banking & Cash")
    const text = container.textContent ?? ""
    const [banking, investments, retirement, liabilities] = order(
      text,
      "Banking & Cash",
      "Investments",
      "Retirement",
      "Liabilities",
    )
    expect(banking).toBeGreaterThanOrEqual(0)
    expect(banking).toBeLessThan(investments)
    expect(investments).toBeLessThan(retirement)
    expect(retirement).toBeLessThan(liabilities)
  })

  it("defaults to value-descending within a group (largest balance first)", async () => {
    const { container } = renderAccounts()
    await screen.findByText("Banking & Cash")
    const [zulu, alpha] = order(container.textContent ?? "", "Zulu Savings", "Alpha Checking")
    expect(zulu).toBeLessThan(alpha) // 9000 before 1000
  })

  it("sorts liabilities by debt magnitude (biggest debt first)", async () => {
    const { container } = renderAccounts()
    await screen.findByText("Liabilities")
    const [mortgage, card] = order(container.textContent ?? "", "Big Mortgage", "Small Card")
    expect(mortgage).toBeLessThan(card) // -200000 magnitude before -500
  })

  it("switches to Name A–Z when the sort control changes", async () => {
    const user = userEvent.setup()
    const { container } = renderAccounts()
    await screen.findByText("Banking & Cash")
    await user.selectOptions(screen.getByLabelText("Sort accounts"), "name_asc")
    await waitFor(() => {
      const [alpha, zulu] = order(container.textContent ?? "", "Alpha Checking", "Zulu Savings")
      expect(alpha).toBeLessThan(zulu)
    })
  })

  it("restores a persisted sort choice from localStorage on mount", async () => {
    localStorage.setItem("hl.accounts.sort", "name_asc")
    const { container } = renderAccounts()
    await screen.findByText("Banking & Cash")
    const [alpha, zulu] = order(container.textContent ?? "", "Alpha Checking", "Zulu Savings")
    expect(alpha).toBeLessThan(zulu) // name_asc applied from storage
  })

  it("falls back to the default sort when the stored value is invalid", async () => {
    localStorage.setItem("hl.accounts.sort", "bogus")
    const { container } = renderAccounts()
    await screen.findByText("Banking & Cash")
    const [zulu, alpha] = order(container.textContent ?? "", "Zulu Savings", "Alpha Checking")
    expect(zulu).toBeLessThan(alpha) // value_desc default
  })
})
