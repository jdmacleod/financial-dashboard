import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import ReportSpending from "@/pages/ReportSpending"

const mockSpending = {
  total: "4200.00",
  categories: [
    {
      category_id: "cat1",
      name: "Housing",
      amount: "2000.00",
      percentage: 47.6,
      transaction_count: 3,
      has_children: true,
    },
    {
      category_id: "cat2",
      name: "Food",
      amount: "800.00",
      percentage: 19.1,
      transaction_count: 10,
      has_children: false,
    },
    {
      category_id: null,
      name: "Uncategorized",
      amount: "1400.00",
      percentage: 33.3,
      transaction_count: 5,
      has_children: false,
    },
  ],
}

// Drilling into cat1 ("Housing") returns its children, not Housing itself —
// mirrors the real API, where parent_category_id filters to sub-categories.
const mockSpendingDrill = {
  total: "2000.00",
  categories: [
    {
      category_id: "cat1a",
      name: "Rent",
      amount: "1500.00",
      percentage: 75.0,
      transaction_count: 2,
      has_children: false,
    },
    {
      category_id: "cat1b",
      name: "Utilities",
      amount: "500.00",
      percentage: 25.0,
      transaction_count: 1,
      has_children: false,
    },
  ],
}

const mockCategories = [
  {
    id: "cat1",
    household_id: "h1",
    name: "Housing",
    slug: "housing",
    parent_category_id: null,
    color_hex: "#3b82f6",
    icon: null,
    is_income: false,
    is_system: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "cat2",
    household_id: "h1",
    name: "Food",
    slug: "food_dining",
    parent_category_id: null,
    color_hex: "#22c55e",
    icon: null,
    is_income: false,
    is_system: true,
    created_at: new Date().toISOString(),
  },
]

let mockSearch: { category?: string; from?: string; to?: string } = {}

vi.mock("@tanstack/react-router", () => ({
  useSearch: () => mockSearch,
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    spendingByCategory: vi.fn((_from: string, _to: string, parentCategoryId?: string) =>
      Promise.resolve(parentCategoryId ? mockSpendingDrill : mockSpending),
    ),
  },
}))

vi.mock("@/api/categories", () => ({
  categoriesApi: {
    list: vi.fn(() => Promise.resolve(mockCategories)),
  },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <ReportSpending />
    </QueryClientProvider>,
  )
}

describe("ReportSpending", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSearch = {}
  })

  it("renders the heading", () => {
    renderPage()
    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument()
  })

  it("shows category names from API", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Housing")).toBeInTheDocument()
      expect(screen.getByText("Food")).toBeInTheDocument()
    })
  })

  it("shows preset period buttons", () => {
    renderPage()
    expect(screen.getByRole("button", { name: "This month" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "3 months" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "6 months" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "12 months" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Custom" })).toBeInTheDocument()
  })

  it("opens in Custom mode on the URL from/to range", async () => {
    mockSearch = { from: "2026-01-01", to: "2026-03-31" }
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await waitFor(() => screen.getByText("Housing"))
    // Date inputs are populated from the URL range...
    expect((screen.getByLabelText("From date") as HTMLInputElement).value).toBe("2026-01-01")
    expect((screen.getByLabelText("To date") as HTMLInputElement).value).toBe("2026-03-31")
    // ...and the report is fetched for exactly that range.
    expect(mock.spendingByCategory).toHaveBeenCalledWith("2026-01-01", "2026-03-31", undefined)
  })

  it("refetches when a custom date input changes", async () => {
    const user = userEvent.setup()
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await user.click(screen.getByRole("button", { name: "Custom" }))
    const from = screen.getByLabelText("From date")
    await user.clear(from)
    await user.type(from, "2025-06-15")
    await waitFor(() => {
      expect(mock.spendingByCategory).toHaveBeenCalledWith(
        "2025-06-15",
        expect.any(String),
        undefined,
      )
    })
  })

  it("warns and skips the query for an inverted custom range", async () => {
    mockSearch = { from: "2026-05-01", to: "2026-02-01" }
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    expect(await screen.findByText(/must be on or before/)).toBeInTheDocument()
    expect(mock.spendingByCategory).not.toHaveBeenCalled()
  })

  it("initializes drillCategory from URL category param", async () => {
    mockSearch = { category: "cat1" }
    const { reportsApi: mock } = await import("@/api/reports")
    renderPage()
    await waitFor(() => screen.getByText("Housing"))
    expect(mock.spendingByCategory).toHaveBeenCalledWith(
      expect.any(String),
      expect.any(String),
      "cat1",
    )
  })

  it("shows All categories back button when drilled", async () => {
    mockSearch = { category: "cat1" }
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "← All categories" })).toBeInTheDocument()
    })
  })

  it("shows the drilled category name in the header and total label", async () => {
    mockSearch = { category: "cat1" }
    renderPage()
    await waitFor(() => screen.getByRole("button", { name: "← All categories" }))
    // The drilled category's name (cat1 → "Housing") resolves from the
    // categories list and appears as a breadcrumb beside the heading...
    await waitFor(() => {
      expect(screen.getByText("Housing")).toBeInTheDocument()
    })
    // ...and the total card is labelled with that category.
    expect(screen.getByText("Total spending: Housing")).toBeInTheDocument()
  })

  it("shows drill down button for has_children=true", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "drill down" })).toBeInTheDocument()
    })
  })

  it("does not show drill down button for has_children=false", async () => {
    renderPage()
    await waitFor(() => screen.getByText("Food"))
    const drillButtons = screen.queryAllByRole("button", { name: "drill down" })
    expect(drillButtons.length).toBe(1)
  })

  it("keeps the drill-down when the time window changes, refetching for the new range", async () => {
    const user = userEvent.setup()
    const { reportsApi: mock } = await import("@/api/reports")
    mockSearch = { category: "cat1" }
    renderPage()
    await waitFor(() => screen.getByRole("button", { name: "← All categories" }))
    await user.click(screen.getByRole("button", { name: "12 months" }))
    // Drill-down stays put: the back button and the drilled breakdown remain...
    await waitFor(() => screen.getByText("Rent"))
    expect(screen.getByRole("button", { name: "← All categories" })).toBeInTheDocument()
    // ...and the report refetched for the new window with the same drill category.
    expect(mock.spendingByCategory).toHaveBeenLastCalledWith(
      expect.any(String),
      expect.any(String),
      "cat1",
    )
  })

  it("exits the drill-down only via the All categories button", async () => {
    const user = userEvent.setup()
    mockSearch = { category: "cat1" }
    renderPage()
    await waitFor(() => screen.getByRole("button", { name: "← All categories" }))
    await user.click(screen.getByRole("button", { name: "← All categories" }))
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "← All categories" })).not.toBeInTheDocument()
    })
  })
})
