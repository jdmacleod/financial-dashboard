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

let mockSearchCategory: string | undefined = undefined

vi.mock("@tanstack/react-router", () => ({
  useSearch: () => ({ category: mockSearchCategory }),
}))

vi.mock("@/api/reports", () => ({
  reportsApi: {
    spendingByCategory: vi.fn(() => Promise.resolve(mockSpending)),
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
    mockSearchCategory = undefined
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
  })

  it("initializes drillCategory from URL category param", async () => {
    mockSearchCategory = "cat1"
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
    mockSearchCategory = "cat1"
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "← All categories" })).toBeInTheDocument()
    })
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

  it("clears drill category when preset button is clicked", async () => {
    const user = userEvent.setup()
    mockSearchCategory = "cat1"
    renderPage()
    await waitFor(() => screen.getByRole("button", { name: "← All categories" }))
    await user.click(screen.getByRole("button", { name: "3 months" }))
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "← All categories" })).not.toBeInTheDocument()
    })
  })
})
