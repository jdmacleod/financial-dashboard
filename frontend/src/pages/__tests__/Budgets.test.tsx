import { render, screen, fireEvent, waitFor, within } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { vi, describe, it, expect, beforeEach } from "vitest"
import Budgets from "../Budgets"
import { budgetsApi } from "@/api/budgets"
import { reportsApi } from "@/api/reports"
import { categoriesApi } from "@/api/categories"
import type { BudgetResponse, BudgetVsActualsReport, CategoryResponse } from "@/api/types"

vi.mock("@/api/budgets", () => ({
  budgetsApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), delete: vi.fn() },
}))
vi.mock("@/api/reports", () => ({
  reportsApi: { budgetVsActuals: vi.fn() },
}))
vi.mock("@/api/categories", () => ({
  categoriesApi: { list: vi.fn() },
}))

const BASE_CAT = {
  household_id: "hh-1",
  parent_category_id: null,
  color_hex: "#000000",
  icon: null,
  is_system: false,
  created_at: "2026-01-01T00:00:00Z",
}
const categories: CategoryResponse[] = [
  { ...BASE_CAT, id: "cat-1", name: "Groceries", is_income: false },
  { ...BASE_CAT, id: "cat-2", name: "Restaurants", is_income: false },
  { ...BASE_CAT, id: "cat-3", name: "Utilities", is_income: false },
]

const budgets: BudgetResponse[] = [
  {
    id: "b-1",
    household_id: "hh-1",
    category_id: "cat-1",
    period: "monthly",
    amount: "500.00",
    effective_from: "2026-01-01",
    effective_to: null,
  },
  {
    id: "b-2",
    household_id: "hh-1",
    category_id: "cat-2",
    period: "monthly",
    amount: "200.00",
    effective_from: "2026-01-01",
    effective_to: null,
  },
  {
    id: "b-3",
    household_id: "hh-1",
    category_id: "cat-3",
    period: "annual",
    amount: "1200.00",
    effective_from: "2026-01-01",
    effective_to: null,
  },
]

const report: BudgetVsActualsReport = {
  period: "2026-06",
  categories: [
    {
      category_id: "cat-1",
      name: "Groceries",
      budget: "500.00",
      actual: "450.00",
      remaining: "50.00",
      percentage_used: 90,
      period: "monthly",
    },
    {
      category_id: "cat-2",
      name: "Restaurants",
      budget: "200.00",
      actual: "220.00",
      remaining: "-20.00",
      percentage_used: 110,
      period: "monthly",
    },
    {
      category_id: "cat-3",
      name: "Utilities",
      budget: "100.00",
      actual: "30.00",
      remaining: "70.00",
      percentage_used: 30,
      period: "annual",
    },
  ],
}

function createClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function renderPage() {
  return render(
    <QueryClientProvider client={createClient()}>
      <Budgets />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(categoriesApi.list).mockResolvedValue(categories)
  vi.mocked(budgetsApi.list).mockResolvedValue(budgets)
  vi.mocked(reportsApi.budgetVsActuals).mockResolvedValue(report)
})

// ── Filter logic ──────────────────────────────────────────────────────────────

describe("filter bar", () => {
  it("shows the filter input when budgets or report data is present", async () => {
    renderPage()
    await waitFor(() =>
      expect(screen.getByPlaceholderText("Filter categories…")).toBeInTheDocument(),
    )
  })

  it("narrows Budget vs Actuals rows by category name (case-insensitive)", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "groc" } })

    const actuals = await screen.findByTestId("section-actuals")
    await waitFor(() => {
      expect(within(actuals).queryByText("Groceries")).toBeInTheDocument()
      expect(within(actuals).queryByText("Restaurants")).not.toBeInTheDocument()
      expect(within(actuals).queryByText("Utilities")).not.toBeInTheDocument()
    })
  })

  it("narrows All Budgets rows by category name", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "util" } })

    const budgetsSection = await screen.findByTestId("section-budgets")
    await waitFor(() => {
      expect(within(budgetsSection).queryByText("Utilities")).toBeInTheDocument()
      expect(within(budgetsSection).queryByText("Groceries")).not.toBeInTheDocument()
    })
  })

  it("shows zero-results state when filter matches nothing", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "zzzzz" } })

    await waitFor(() => {
      expect(screen.getAllByText(/No categories match/i).length).toBeGreaterThan(0)
    })
  })

  it("Clear button resets filter and restores all rows", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "groc" } })

    const actuals = await screen.findByTestId("section-actuals")
    await waitFor(() => expect(within(actuals).queryByText("Restaurants")).not.toBeInTheDocument())

    const clearBtn = screen.getByRole("button", { name: "Clear" })
    fireEvent.click(clearBtn)

    await waitFor(() => expect(within(actuals).queryByText("Restaurants")).toBeInTheDocument())
  })

  it("count badge appears when filter is active (Budget vs Actuals count)", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "g" } })

    await waitFor(() => {
      // "1 of 3" — only Groceries matches "g"
      expect(screen.getByText(/\d+ of \d+/)).toBeInTheDocument()
    })
  })
})

// ── Budget vs Actuals sort ────────────────────────────────────────────────────

describe("Budget vs Actuals sort", () => {
  it("defaults to % used descending (Restaurants 110% first)", async () => {
    renderPage()
    const actuals = await screen.findByTestId("section-actuals")

    await waitFor(() => {
      // category name spans: text-sm font-medium — scoped to this section
      const names = within(actuals)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      // Restaurants (110%) > Groceries (90%) > Utilities (30%)
      expect(names[0]).toBe("Restaurants")
      expect(names[1]).toBe("Groceries")
    })
  })

  it("Name A-Z sort places Groceries before Restaurants before Utilities", async () => {
    renderPage()
    const actuals = await screen.findByTestId("section-actuals")
    const select = within(actuals).getByRole("combobox", { name: "Sort budget vs actuals" })
    fireEvent.change(select, { target: { value: "name_asc" } })

    await waitFor(() => {
      const names = within(actuals)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      expect(names[0]).toBe("Groceries")
      expect(names[1]).toBe("Restaurants")
      expect(names[2]).toBe("Utilities")
    })
  })

  it("Budget ↓ sort places Groceries (500) before Restaurants (200)", async () => {
    renderPage()
    const actuals = await screen.findByTestId("section-actuals")
    const select = within(actuals).getByRole("combobox", { name: "Sort budget vs actuals" })
    fireEvent.change(select, { target: { value: "budget_desc" } })

    await waitFor(() => {
      const names = within(actuals)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      expect(names[0]).toBe("Groceries")
    })
  })

  it("Actual Spend ↓ sort places Groceries (450) before Restaurants (220)", async () => {
    renderPage()
    const actuals = await screen.findByTestId("section-actuals")
    const select = within(actuals).getByRole("combobox", { name: "Sort budget vs actuals" })
    fireEvent.change(select, { target: { value: "actual_desc" } })

    await waitFor(() => {
      const names = within(actuals)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      // Groceries actual=450 > Restaurants actual=220 > Utilities actual=30
      expect(names[0]).toBe("Groceries")
      expect(names[1]).toBe("Restaurants")
    })
  })
})

// ── All Budgets sort ──────────────────────────────────────────────────────────

describe("All Budgets sort", () => {
  it("defaults to Name A-Z (Groceries first)", async () => {
    renderPage()
    const budgetsSection = await screen.findByTestId("section-budgets")

    await waitFor(() => {
      const names = within(budgetsSection)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      expect(names[0]).toBe("Groceries")
      expect(names[1]).toBe("Restaurants")
      expect(names[2]).toBe("Utilities")
    })
  })

  it("Budget ↓ sort places Utilities (1200) first, then Groceries (500), then Restaurants (200)", async () => {
    renderPage()
    const budgetsSection = await screen.findByTestId("section-budgets")
    const select = within(budgetsSection).getByRole("combobox", { name: "Sort all budgets" })
    fireEvent.change(select, { target: { value: "budget_desc" } })

    await waitFor(() => {
      const names = within(budgetsSection)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      expect(names[0]).toBe("Utilities")
      expect(names[1]).toBe("Groceries")
    })
  })

  it("Period sort places monthly budgets before annual (Utilities last)", async () => {
    renderPage()
    const budgetsSection = await screen.findByTestId("section-budgets")
    const select = within(budgetsSection).getByRole("combobox", { name: "Sort all budgets" })
    fireEvent.change(select, { target: { value: "period" } })

    await waitFor(() => {
      const names = within(budgetsSection)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      expect(names[names.length - 1]).toBe("Utilities")
    })
  })

  it("Period sort — same-period tie-break is alphabetical (Groceries before Restaurants)", async () => {
    renderPage()
    const budgetsSection = await screen.findByTestId("section-budgets")
    const select = within(budgetsSection).getByRole("combobox", { name: "Sort all budgets" })
    fireEvent.change(select, { target: { value: "period" } })

    await waitFor(() => {
      const names = within(budgetsSection)
        .getAllByText(/^(Groceries|Restaurants|Utilities)$/)
        .map((el) => el.textContent)
      // Both Groceries and Restaurants are monthly — alphabetical tie-break
      const grocIdx = names.indexOf("Groceries")
      const restIdx = names.indexOf("Restaurants")
      expect(grocIdx).toBeLessThan(restIdx)
    })
  })
})

// ── Edge cases ────────────────────────────────────────────────────────────────

describe("edge cases", () => {
  it("filter bar is hidden when both budgets and report items are empty", async () => {
    vi.mocked(budgetsApi.list).mockResolvedValue([])
    vi.mocked(reportsApi.budgetVsActuals).mockResolvedValue({
      period: "2026-06",
      categories: [],
    })
    renderPage()
    await waitFor(() => {
      expect(screen.queryByPlaceholderText("Filter categories…")).not.toBeInTheDocument()
    })
  })

  it("inline Clear filter link inside zero-results actuals state resets the filter", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "zzzzz" } })

    const actuals = await screen.findByTestId("section-actuals")
    const inlineClear = await within(actuals).findByRole("button", { name: "Clear filter" })
    fireEvent.click(inlineClear)

    await waitFor(() => expect(input).toHaveValue(""))
  })

  it("inline Clear filter link inside zero-results budgets state resets the filter", async () => {
    renderPage()
    const input = await screen.findByPlaceholderText("Filter categories…")
    fireEvent.change(input, { target: { value: "zzzzz" } })

    const budgetsSection = await screen.findByTestId("section-budgets")
    const inlineClear = await within(budgetsSection).findByRole("button", { name: "Clear filter" })
    fireEvent.click(inlineClear)

    await waitFor(() => expect(input).toHaveValue(""))
  })
})
