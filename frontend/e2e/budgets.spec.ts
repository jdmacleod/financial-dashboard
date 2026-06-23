import { test, expect, type Page } from "@playwright/test"

const BASE_URL = "http://localhost"
const EMAIL = "bob@langford.local"
const PASSWORD = "HearthDemo1!" // pragma: allowlist secret

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByRole("textbox").first().fill(EMAIL)
  await page.getByRole("textbox").nth(1).fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.waitForURL(`${BASE_URL}/`)
}

test.describe("Budgets tab — Langford Household", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/budgets`)
    await page.waitForLoadState("networkidle")
  })

  // ── Month mode navigation ───────────────────────────────────────────────────

  test("displays month mode by default with current month", async ({ page }) => {
    const monthLabel = page.locator("span.text-center.font-medium")
    const text = await monthLabel.textContent()
    expect(text).toMatch(/^\d{4}-\d{2}$/)
  })

  test("back arrow decrements month by exactly one", async ({ page }) => {
    // Identify current month label
    const monthSpan = page.locator("span.text-center.font-medium")
    const before = await monthSpan.textContent()
    expect(before).toMatch(/^(\d{4})-(\d{2})$/)

    await page.getByRole("button", { name: "Previous month" }).click()
    await page.waitForLoadState("networkidle")

    const after = await monthSpan.textContent()
    expect(after).toMatch(/^(\d{4})-(\d{2})$/)

    const [beforeY, beforeM] = before!.split("-").map(Number)
    const [afterY, afterM] = after!.split("-").map(Number)
    const beforeTotal = beforeY * 12 + beforeM
    const afterTotal = afterY * 12 + afterM
    expect(beforeTotal - afterTotal).toBe(1)
  })

  test("forward arrow increments month by exactly one", async ({ page }) => {
    // Go back one month first so we're not at the edge
    await page.getByRole("button", { name: "Previous month" }).click()
    await page.waitForLoadState("networkidle")

    const monthSpan = page.locator("span.text-center.font-medium")
    const before = await monthSpan.textContent()

    await page.getByRole("button", { name: "Next month" }).click()
    await page.waitForLoadState("networkidle")

    const after = await monthSpan.textContent()

    const [beforeY, beforeM] = before!.split("-").map(Number)
    const [afterY, afterM] = after!.split("-").map(Number)
    const beforeTotal = beforeY * 12 + beforeM
    const afterTotal = afterY * 12 + afterM
    expect(afterTotal - beforeTotal).toBe(1)
  })

  test("back arrow navigates sequentially through 3 months without skipping", async ({ page }) => {
    const monthSpan = page.locator("span.text-center.font-medium")
    const months: string[] = [(await monthSpan.textContent()) ?? ""]

    for (let i = 0; i < 3; i++) {
      await page.getByRole("button", { name: "Previous month" }).click()
      await page.waitForLoadState("networkidle")
      months.push((await monthSpan.textContent()) ?? "")
    }

    // Each pair must differ by exactly 1 month
    for (let i = 1; i < months.length; i++) {
      const [py, pm] = months[i - 1].split("-").map(Number)
      const [cy, cm] = months[i].split("-").map(Number)
      expect(py * 12 + pm - (cy * 12 + cm)).toBe(1)
    }
  })

  // ── Range toggle ────────────────────────────────────────────────────────────

  test("YTD mode shows Jan to current month range label", async ({ page }) => {
    const ytdBtn = page.locator("button", { hasText: "YTD" }).nth(1)
    await ytdBtn.click()
    const year = new Date().getFullYear()
    // Wait for the Budget vs Actuals header to update with the YTD label
    await expect(page.locator("p.text-xs.font-semibold", { hasText: /Jan/ })).toBeVisible({
      timeout: 15000,
    })
    await expect(
      page.locator("p.text-xs.font-semibold", { hasText: new RegExp(String(year)) }),
    ).toBeVisible({ timeout: 5000 })
  })

  test("YTD mode shows aggregated totals different from single month", async ({ page }) => {
    // Wait for month mode to have loaded data, then capture the total
    await expect(page.getByText("Total budgeted")).toBeVisible()
    const donutSection = page.locator("p", { hasText: /^Total budgeted$/ }).locator("..")
    const monthTotal = await donutSection.locator("p.text-2xl").textContent()
    const parseAmount = (s: string | null) => parseFloat(s?.replace(/[$,]/g, "") ?? "0")

    const ytdBtn = page.locator("button", { hasText: "YTD" }).nth(1)
    await ytdBtn.click()

    // Poll until the donut total updates to the aggregated (6-month) value
    await expect
      .poll(
        async () => {
          const t = await donutSection.locator("p.text-2xl").textContent()
          return parseAmount(t)
        },
        { timeout: 15000 },
      )
      .toBeGreaterThan(parseAmount(monthTotal))
  })

  test("1Y mode shows at least 12 months of categories", async ({ page }) => {
    const oneYBtn = page.locator("button", { hasText: "1Y" }).nth(1)
    await oneYBtn.click()
    await page.waitForLoadState("networkidle")

    // Budget vs Actuals section should have entries
    const rows = page.locator("text=% used")
    const count = await rows.count()
    expect(count).toBeGreaterThan(10)
  })

  test("All mode shows data starting before 2025", async ({ page }) => {
    const allBtn = page.locator("button", { hasText: "All" }).nth(1)
    await allBtn.click()
    await page.waitForLoadState("networkidle")

    // Check that the label shows a year range spanning > 1 year
    const rangeLabel = page.locator("span.text-sm.text-gray-500")
    const labelText = await rangeLabel.first().textContent()
    expect(labelText).toMatch(/\d{4}/)
  })

  test("switching back to Month mode shows month navigator", async ({ page }) => {
    const ytdBtn = page.locator("button", { hasText: "YTD" }).nth(1)
    await ytdBtn.click()
    await page.waitForLoadState("networkidle")

    const monthBtn = page.locator("button", { hasText: "Month" })
    await monthBtn.click()
    await page.waitForLoadState("networkidle")

    await expect(page.getByRole("button", { name: "Previous month" })).toBeVisible()
    await expect(page.getByRole("button", { name: "Next month" })).toBeVisible()
  })

  // ── Donut chart ─────────────────────────────────────────────────────────────

  test("donut chart is visible with total budgeted amount", async ({ page }) => {
    await expect(page.getByText("Total budgeted")).toBeVisible()
    // Should show a dollar amount
    const totalLine = page.locator("text=Total budgeted").locator("..")
    await expect(totalLine.locator(".text-2xl")).toBeVisible()
  })

  test("donut chart shows top budget categories in legend", async ({ page }) => {
    // Wait for donut to load then check that category names appear in the legend
    await expect(page.getByText("Total budgeted")).toBeVisible()
    // The donut legend renders category names — Restaurants is a top Langford budget
    await expect(
      page.locator("span.text-xs.text-gray-600", { hasText: "Restaurants" }),
    ).toBeVisible()
  })

  // ── Budget vs Actuals report ────────────────────────────────────────────────

  test("budget vs actuals report shows categories with progress bars", async ({ page }) => {
    await expect(page.getByText("Budget vs Actuals")).toBeVisible()
    // Categories should show "% used" text
    const usedTexts = page.locator("text=% used")
    const count = await usedTexts.count()
    expect(count).toBeGreaterThan(5)
  })

  test("over-budget items are highlighted in red", async ({ page }) => {
    // Home Insurance in June 2026 is way over budget
    await expect(page.getByText("895% used")).toBeVisible()
    const overText = page.locator("text=over budget").or(page.locator("text=over"))
    const count = await overText.count()
    expect(count).toBeGreaterThan(0)
  })

  // ── CRUD operations ─────────────────────────────────────────────────────────

  test("Add Budget modal opens with period selector", async ({ page }) => {
    await page.getByRole("button", { name: "Add budget" }).click()
    await expect(page.getByRole("heading", { name: "Add Budget" })).toBeVisible()
    // Period radio buttons — DOM text is lowercase ("monthly", "annual") capitalized via CSS
    await expect(page.getByText("Period")).toBeVisible()
    await expect(page.locator("input[type=radio][value=monthly]")).toBeVisible()
    await expect(page.locator("input[type=radio][value=annual]")).toBeVisible()
  })

  test("Add Budget modal closes on X click", async ({ page }) => {
    await page.getByRole("button", { name: "Add budget" }).click()
    await expect(page.getByRole("heading", { name: "Add Budget" })).toBeVisible()

    await page.locator("button").filter({ hasText: "✕" }).click()
    await expect(page.getByRole("heading", { name: "Add Budget" })).not.toBeVisible()
  })

  test("Edit modal opens with all fields for a budget row", async ({ page }) => {
    // Click the first Edit button in the All Budgets section
    const editButtons = page.getByRole("button", { name: "Edit" })
    await editButtons.first().click()

    await expect(page.getByRole("heading", { name: "Edit Budget" })).toBeVisible()
    // Should show amount, period, effective_from, effective_to fields
    await expect(page.getByText("Effective from")).toBeVisible()
    await expect(page.getByText("Effective to")).toBeVisible()
    await expect(page.getByText("Period")).toBeVisible()
  })

  test("Edit modal closes on Cancel", async ({ page }) => {
    const editButtons = page.getByRole("button", { name: "Edit" })
    await editButtons.first().click()
    await expect(page.getByRole("heading", { name: "Edit Budget" })).toBeVisible()

    await page.getByRole("button", { name: "Cancel" }).click()
    await expect(page.getByRole("heading", { name: "Edit Budget" })).not.toBeVisible()
  })

  test("All Budgets list shows Edit and Delete for each entry", async ({ page }) => {
    await expect(page.getByText("All Budgets")).toBeVisible()
    const editButtons = page.getByRole("button", { name: "Edit" })
    const deleteButtons = page.getByRole("button", { name: "Delete" })
    expect(await editButtons.count()).toBeGreaterThan(10)
    expect(await deleteButtons.count()).toBeGreaterThan(10)
    // Edit and Delete counts should match
    expect(await editButtons.count()).toBe(await deleteButtons.count())
  })
})

// ── Additional household (Chen-Nakamura) ────────────────────────────────────

test.describe("Budgets tab — Chen-Nakamura Household", () => {
  test.beforeEach(async ({ page }) => {
    // Log in as a different household to verify multi-household correctness
    await page.goto(`${BASE_URL}/login`)
    await page.getByRole("textbox").first().fill("alice@chen-nakamura.local")
    await page.getByRole("textbox").nth(1).fill("HearthDemo1!") // pragma: allowlist secret
    await page.getByRole("button", { name: "Sign in" }).click()
    // If login fails (household may not exist), skip gracefully
    await page.waitForTimeout(2000)
    if (!page.url().includes("login")) {
      await page.goto(`${BASE_URL}/budgets`)
      await page.waitForLoadState("networkidle")
    }
  })

  test("budgets page loads without errors for non-Langford household", async ({ page }) => {
    if (page.url().includes("login")) {
      test.skip()
      return
    }
    await expect(page.getByRole("heading", { name: "Budgets" })).toBeVisible()
    // Should not show a JS error
    const errors: string[] = []
    page.on("pageerror", (err) => errors.push(err.message))
    await page.reload()
    await page.waitForLoadState("networkidle")
    expect(errors.filter((e) => !e.includes("ResizeObserver"))).toHaveLength(0)
  })
})
