import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest"
import { AppLayout } from "../AppLayout"
import { createClient, wrapper } from "@/test/testUtils"

// ── Router mocks ──────────────────────────────────────────────────────────────
const mockNavigate = vi.fn()
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    to,
    children,
    onClick,
    ...rest
  }: {
    to: string
    children: React.ReactNode
    onClick?: () => void
    [k: string]: unknown
  }) => (
    <a href={to} onClick={onClick} data-to={to} {...rest}>
      {children}
    </a>
  ),
  Outlet: () => <div data-testid="outlet" />,
  useNavigate: () => mockNavigate,
  useRouterState: ({
    select,
  }: {
    select: (s: { location: { pathname: string; search: string } }) => unknown
  }) => select({ location: { pathname: "/", search: "" } }),
}))

// ── Auth / user mocks ─────────────────────────────────────────────────────────
const mockLogout = vi.fn().mockResolvedValue(undefined)
vi.mock("@/hooks/useAuth", () => ({
  useAuth: (
    selector: (s: { role: string; logout: () => Promise<void>; memberId: string }) => unknown,
  ) => selector({ role: "primary", logout: mockLogout, memberId: "m1" }),
}))

vi.mock("@/hooks/useCurrentUser", () => ({
  useCurrentUser: () => ({
    displayName: "Jane Smith",
    firstName: "Jane",
    initials: "JS",
    householdName: "Smith Household",
    role: "primary",
    isLoading: false,
  }),
}))

// ── API mocks ─────────────────────────────────────────────────────────────────
vi.mock("@/api/accounts", () => ({
  accountsApi: {
    list: vi.fn().mockResolvedValue([{ id: "a1" }, { id: "a2" }, { id: "a3" }]),
  },
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    dashboard: vi.fn().mockResolvedValue({
      net_worth: { current: "425000.00", change_30d: "1200.00", change_30d_pct: 0.28 },
      cash_flow_mtd: { income: "5000.00", expenses: "3200.00", net: "1800.00" },
      top_spending_categories: [],
      budget_alerts: [],
      accounts_summary: { total_assets: "500000.00", total_liabilities: "75000.00" },
    }),
  },
}))

vi.mock("@/components/app/ExportModal", () => ({
  ExportModal: ({ open }: { open: boolean }) => (open ? <div data-testid="export-modal" /> : null),
}))

// ── Theme store ───────────────────────────────────────────────────────────────
const mockSetTheme = vi.fn()
vi.mock("@/stores/themeStore", () => ({
  useTheme: () => ({ theme: "dark", setTheme: mockSetTheme }),
}))

// ── Helpers ───────────────────────────────────────────────────────────────────
function renderLayout() {
  const client = createClient()
  return render(<AppLayout />, { wrapper: wrapper(client) })
}

describe("AppLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.removeAttribute("data-theme")
    localStorage.clear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe("sidebar nav", () => {
    it("renders all primary nav items", () => {
      renderLayout()
      expect(screen.getByText("Overview")).toBeInTheDocument()
      expect(screen.getByText("Accounts")).toBeInTheDocument()
      expect(screen.getByText("Investments")).toBeInTheDocument()
      expect(screen.getByText("Retirement")).toBeInTheDocument()
      expect(screen.getByText("Real estate")).toBeInTheDocument()
      expect(screen.getByText("Cash flow")).toBeInTheDocument()
    })

    it("renders planning section with FIRE, Debt, Budgets", () => {
      renderLayout()
      expect(screen.getByText("Planning")).toBeInTheDocument()
      expect(screen.getByText("FIRE")).toBeInTheDocument()
      expect(screen.getByText("Debt")).toBeInTheDocument()
      expect(screen.getByText("Budgets")).toBeInTheDocument()
    })

    it("shows household name in brand mark", () => {
      renderLayout()
      expect(screen.getAllByText("Smith Household").length).toBeGreaterThan(0)
    })

    it("renders Outlet for child pages", () => {
      renderLayout()
      expect(screen.getByTestId("outlet")).toBeInTheDocument()
    })
  })

  describe("sidebar footer", () => {
    it("shows net worth from dashboard API", async () => {
      renderLayout()
      await waitFor(() => {
        expect(screen.getByText("$425,000.00")).toBeInTheDocument()
      })
    })
  })

  describe("header", () => {
    it("shows account count from accounts API", async () => {
      renderLayout()
      await waitFor(() => {
        expect(screen.getByText(/3 accounts/)).toBeInTheDocument()
      })
    })

    it("renders range toggle with YTD, 1Y, All buttons", () => {
      renderLayout()
      expect(screen.getByRole("button", { name: "YTD" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "1Y" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument()
    })

    it("calls navigate with range=1y when 1Y button is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: "1Y" }))
      expect(mockNavigate).toHaveBeenCalledWith(expect.objectContaining({ replace: true }))
    })
  })

  describe("identity widget", () => {
    it("shows user first name in the trigger button", () => {
      renderLayout()
      expect(screen.getByText("Jane")).toBeInTheDocument()
    })

    it("opens dropdown when identity button is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      const trigger = screen.getByRole("button", { name: /User menu/ })
      await user.click(trigger)
      expect(screen.getByRole("menu")).toBeInTheDocument()
    })

    it("shows user display name in open dropdown", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      expect(screen.getByText("Jane Smith")).toBeInTheDocument()
    })

    it("closes dropdown on Escape key", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      expect(screen.getByRole("menu")).toBeInTheDocument()
      await user.keyboard("{Escape}")
      expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    })

    it("closes dropdown on outside click", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      expect(screen.getByRole("menu")).toBeInTheDocument()
      await user.click(document.body)
      expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    })

    it("shows appearance toggle in open dropdown", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      expect(screen.getByText("Appearance")).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Dark" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "Light" })).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "System" })).toBeInTheDocument()
    })

    it("calls setTheme when an appearance option is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      await user.click(screen.getByRole("button", { name: "Light" }))
      expect(mockSetTheme).toHaveBeenCalledWith("light")
    })

    it("opens export modal when Export is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      const exportBtn = screen.getByRole("button", { name: "Export" })
      await user.click(exportBtn)
      expect(screen.getByTestId("export-modal")).toBeInTheDocument()
    })

    it("calls logout and navigates to /login when Sign out is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: /User menu/ }))
      await user.click(screen.getByRole("button", { name: "Sign out" }))
      await waitFor(() => {
        expect(mockLogout).toHaveBeenCalled()
        expect(mockNavigate).toHaveBeenCalledWith({ to: "/login" })
      })
    })
  })

  describe("mobile hamburger", () => {
    it("renders a hamburger button in the header", () => {
      renderLayout()
      expect(screen.getByRole("button", { name: "Open navigation" })).toBeInTheDocument()
    })

    it("opens mobile overlay when hamburger is clicked", async () => {
      const user = userEvent.setup()
      renderLayout()
      // The sidebar is rendered twice when overlay is open (desktop + mobile overlay)
      await user.click(screen.getByRole("button", { name: "Open navigation" }))
      expect(screen.getAllByText("Overview").length).toBeGreaterThan(1)
    })

    it("closes mobile overlay on Escape key", async () => {
      const user = userEvent.setup()
      renderLayout()
      await user.click(screen.getByRole("button", { name: "Open navigation" }))
      expect(screen.getAllByText("Overview").length).toBeGreaterThan(1)
      await user.keyboard("{Escape}")
      expect(screen.getAllByText("Overview").length).toBe(1)
    })
  })
})
