import { test, expect, type Page } from "@playwright/test"

const BASE_URL = "http://localhost"
const EMAIL = "zoe@park-cole.local"
const PASSWORD = "HearthDemo1!" // pragma: allowlist secret

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByRole("textbox").first().fill(EMAIL)
  await page.getByRole("textbox").nth(1).fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.waitForURL(`${BASE_URL}/`)
}

test.describe("Reports — fixes and new reports", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test("Net Worth liabilities amortize over time (not a flat line)", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/net-worth`)
    await page.waitForLoadState("networkidle")
    await page.getByRole("button", { name: "2 Years" }).click()
    await page.waitForTimeout(800)

    const rows = page.locator("table tbody tr")
    const n = await rows.count()
    expect(n).toBeGreaterThan(12)

    const liabs: number[] = []
    for (let i = 0; i < n; i++) {
      const cell = await rows.nth(i).locator("td").nth(2).textContent()
      liabs.push(Number((cell ?? "0").replace(/[^0-9.-]/g, "")))
    }
    // Park-Cole carries amortizing student loans: the liability line must move
    // across months and decline from oldest to newest (payments post over time).
    const distinct = new Set(liabs.map((v) => Math.round(v)))
    expect(distinct.size).toBeGreaterThan(3)
    expect(liabs[n - 1]).toBeGreaterThan(liabs[0])
  })

  test("Debt page reflects amortized current balances", async ({ page }) => {
    await page.goto(`${BASE_URL}/debt`)
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(600)
    const text = (await page.locator("body").textContent()) ?? ""
    expect(text).toContain("16,421")
    expect(text).toContain("19,011")
  })

  test("Spending donut has a centered total and no in-chart legend", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/spending`)
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(800)
    const card = page.locator("div.bg-white").filter({ hasText: "Total spending" }).first()
    await expect(card.getByText(/categories$/)).toBeVisible()
    // The old wrapping in-SVG legend rendered category names as <Legend> text
    // inside the chart; the breakdown panel is now the only legend.
    await expect(card.locator(".recharts-legend-wrapper")).toHaveCount(0)
  })

  test("Savings Rate report renders with an average rate", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/savings-rate`)
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(800)
    await expect(page.getByRole("heading", { name: "Savings Rate" })).toBeVisible()
    await expect(
      page.locator("div.bg-white.rounded-xl").filter({ hasText: "Average rate" }),
    ).toBeVisible()
  })

  test("Budget Trend report renders", async ({ page }) => {
    await page.goto(`${BASE_URL}/reports/budget-trend`)
    await page.waitForLoadState("networkidle")
    await page.waitForTimeout(800)
    await expect(page.getByRole("heading", { name: "Budget Trend" })).toBeVisible()
    await expect(
      page.locator("div.bg-white.rounded-xl").filter({ hasText: "Total budgeted" }),
    ).toBeVisible()
  })
})
