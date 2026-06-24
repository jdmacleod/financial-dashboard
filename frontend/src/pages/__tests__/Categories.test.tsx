import { render, screen, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Categories from "@/pages/Categories"

const mockCategories = [
  {
    id: "p1",
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
    id: "c1",
    household_id: "h1",
    name: "Rent",
    slug: "rent",
    parent_category_id: "p1",
    color_hex: "#888888",
    icon: null,
    is_income: false,
    is_system: true,
    created_at: new Date().toISOString(),
  },
  {
    id: "p2",
    household_id: "h1",
    name: "My Category",
    slug: null,
    parent_category_id: null,
    color_hex: "#ff0000",
    icon: null,
    is_income: false,
    is_system: false,
    created_at: new Date().toISOString(),
  },
]

vi.mock("@/api/categories", () => ({
  categoriesApi: {
    list: vi.fn(() => Promise.resolve(mockCategories)),
    create: vi.fn(() => Promise.resolve(mockCategories[0])),
    update: vi.fn(() => Promise.resolve(mockCategories[0])),
    delete: vi.fn(() => Promise.resolve()),
  },
}))

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <Categories />
    </QueryClientProvider>,
  )
}

describe("Categories page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders the heading", () => {
    renderPage()
    expect(screen.getByRole("heading", { name: "Categories" })).toBeInTheDocument()
  })

  it("shows parent and child category names", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Housing")).toBeInTheDocument()
      expect(screen.getByText("Rent")).toBeInTheDocument()
    })
  })

  it("shows SYSTEM badge for system categories", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText("SYSTEM").length).toBeGreaterThan(0)
    })
  })

  it("does not show Rename or Delete for system categories", async () => {
    renderPage()
    await waitFor(() => screen.getByText("Housing"))
    // Scope to the Housing parent row — custom categories may have Rename buttons
    const housingRow = screen.getByText("Housing").closest("div")!
    expect(housingRow).toBeTruthy()
    expect(within(housingRow).queryByRole("button", { name: "Rename" })).not.toBeInTheDocument()
    expect(within(housingRow).queryByRole("button", { name: "Delete" })).not.toBeInTheDocument()
  })

  it("shows Rename and Delete for custom categories", async () => {
    renderPage()
    // "My Category" appears as a parent row span AND as a parent-selector option
    await waitFor(() => {
      expect(screen.getAllByText("My Category").length).toBeGreaterThan(0)
    })
    expect(screen.getByRole("button", { name: "Rename" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument()
  })

  it("shows Income and Expense section labels", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText("Income")).toBeInTheDocument()
      expect(screen.getByText("Expense")).toBeInTheDocument()
    })
  })

  it("shows Add button in the form", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: "Add" }).length).toBeGreaterThan(0)
    })
  })

  it("shows parent selector dropdown in add form", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByRole("combobox").length).toBeGreaterThan(0)
    })
  })
})
