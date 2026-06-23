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

test.describe("Cash Flow tab", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  // ── Capitalization ──────────────────────────────────────────────────────────

  test("sidebar nav shows 'Cash Flow' and 'Real Estate' (both words capitalized)", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow`)
    await page.waitForLoadState("networkidle")

    const nav = page.locator("nav")
    await expect(nav.getByText("Cash Flow", { exact: true })).toBeVisible()
    await expect(nav.getByText("Real Estate", { exact: true })).toBeVisible()

    // Ensure old casing is gone
    await expect(nav.getByText("Cash flow", { exact: true })).toHaveCount(0)
    await expect(nav.getByText("Real estate", { exact: true })).toHaveCount(0)
  })

  test("page heading reads 'Cash Flow'", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow`)
    await page.waitForLoadState("networkidle")

    const heading = page.getByRole("heading", { level: 1 })
    await expect(heading).toHaveText("Cash Flow")
  })

  // ── Date range toggle ───────────────────────────────────────────────────────

  test("YTD range shows correct Langford totals and Jan–Jun period labels", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=ytd`)
    await page.waitForLoadState("networkidle")

    // Langford YTD figures
    await expect(page.getByText("$149,451.97")).toBeVisible()
    await expect(page.getByText("$131,393.08")).toBeVisible()
    await expect(page.getByText("$18,058.89")).toBeVisible()
    await expect(page.getByText("12.1%")).toBeVisible()

    // Period table shows human-readable labels
    const periodTable = page.locator("table")
    await expect(periodTable.getByText("Jan 2026")).toBeVisible()
    await expect(periodTable.getByText("Jun 2026")).toBeVisible()

    // No raw ISO dates in the table
    await expect(periodTable.getByText("2026-01")).toHaveCount(0)
    await expect(periodTable.getByText("2026-06")).toHaveCount(0)
  })

  test("1Y range shows at least 12 months of data with human-readable period labels", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=1y`)
    await page.waitForLoadState("networkidle")

    // 1Y window (365 days back from Jun 23 2026) may span 12-13 months
    const rows = page.locator("table tbody tr")
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(12)

    // All period labels must be human-readable (e.g. "Jun 2026", not "2026-06")
    const cells = page.locator("table tbody tr td:first-child")
    for (let i = 0; i < count; i++) {
      const text = await cells.nth(i).textContent()
      expect(text).toMatch(/^[A-Z][a-z]{2} \d{4}$/)
    }
  })

  test("All range shows at least 24 months of data with human-readable period labels", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=all`)
    await page.waitForLoadState("networkidle")

    const rows = page.locator("table tbody tr")
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(24)

    // All period labels must be human-readable
    const cells = page.locator("table tbody tr td:first-child")
    for (let i = 0; i < Math.min(count, 5); i++) {
      const text = await cells.nth(i).textContent()
      expect(text).toMatch(/^[A-Z][a-z]{2} \d{4}$/)
    }
  })

  // ── Month / Quarter grouping ────────────────────────────────────────────────

  test("Month grouping (default) shows monthly period rows with 'Mon YYYY' labels", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=ytd`)
    await page.waitForLoadState("networkidle")

    // Month button exists and is the active tab
    await expect(page.getByRole("button", { name: /^month$/i })).toBeVisible()

    // 6 rows for Jan–Jun 2026 YTD
    const rows = page.locator("table tbody tr")
    await expect(rows).toHaveCount(6)

    // Period label format: "Jun 2026" not "2026-06"
    await expect(page.locator("table").getByText("Jun 2026")).toBeVisible()
    await expect(page.locator("table").getByText("Jan 2026")).toBeVisible()
  })

  test("Quarter grouping shows Q-label rows (Q1 2026, Q2 2026) for YTD", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=ytd`)
    await page.waitForLoadState("networkidle")

    await page.getByRole("button", { name: /^quarter$/i }).click()
    await page.waitForLoadState("networkidle")

    // Q1 and Q2 for YTD 2026
    const rows = page.locator("table tbody tr")
    await expect(rows).toHaveCount(2)

    await expect(page.locator("table tbody").getByText("Q1 2026")).toBeVisible()
    await expect(page.locator("table tbody").getByText("Q2 2026")).toBeVisible()

    // No ISO format in table
    await expect(page.locator("table").getByText("2026-Q1")).toHaveCount(0)
    await expect(page.locator("table").getByText("2026-Q2")).toHaveCount(0)
  })

  test("Quarter grouping with 1Y range shows at least 4 quarters", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=1y`)
    await page.waitForLoadState("networkidle")

    await page.getByRole("button", { name: /^quarter$/i }).click()
    // Wait for table rows to appear after the groupBy refetch
    await expect(page.locator("table tbody tr").first()).toBeVisible()

    const rows = page.locator("table tbody tr")
    const count = await rows.count()
    expect(count).toBeGreaterThanOrEqual(4)

    // All period labels must be Q-format
    const cells = page.locator("table tbody tr td:first-child")
    for (let i = 0; i < count; i++) {
      const text = await cells.nth(i).textContent()
      expect(text).toMatch(/^Q[1-4] \d{4}$/)
    }
  })

  // ── XAxis labels (via visible page text) ───────────────────────────────────

  test("bar chart XAxis shows month labels like 'Jan 2026' for month grouping", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=ytd`)
    await page.waitForLoadState("networkidle")

    // The XAxis tick labels are in the SVG; getByText finds them anywhere on the page
    await expect(page.getByText("Jan 2026").first()).toBeVisible()
    await expect(page.getByText("Jun 2026").first()).toBeVisible()

    // No raw ISO format visible anywhere
    await expect(page.getByText("2026-01")).toHaveCount(0)
    await expect(page.getByText("2026-06")).toHaveCount(0)
  })

  test("bar chart XAxis shows Q-labels like 'Q1 2026' for quarter grouping", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/cash-flow?range=ytd`)
    await page.waitForLoadState("networkidle")

    await page.getByRole("button", { name: /^quarter$/i }).click()
    await page.waitForLoadState("networkidle")

    await expect(page.getByText("Q1 2026").first()).toBeVisible()
    await expect(page.getByText("Q2 2026").first()).toBeVisible()

    // No raw ISO format visible
    await expect(page.getByText("2026-Q1")).toHaveCount(0)
    await expect(page.getByText("2026-Q2")).toHaveCount(0)
  })
})
