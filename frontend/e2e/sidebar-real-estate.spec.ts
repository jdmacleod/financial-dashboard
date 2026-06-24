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

test.describe("Sidebar — Real Estate highlight", () => {
  test.beforeEach(async ({ page }) => {
    await login(page)
  })

  test("Real Estate nav item is active on the /real-estate list page", async ({ page }) => {
    await page.goto(`${BASE_URL}/real-estate`)
    await page.waitForLoadState("networkidle")
    const link = page.locator("nav a").filter({ hasText: /^Real Estate$/ })
    const style = await link.getAttribute("style")
    expect(style).toContain("var(--nav-active-bg)")
  })

  test("Real Estate nav item stays active when viewing a property detail page", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/real-estate`)
    await page.waitForLoadState("networkidle")

    const propertyLinks = page.locator('a[href*="/real-estate/"]').filter({
      hasNot: page.locator('[href="/real-estate"]'),
    })
    const count = await propertyLinks.count()
    if (count === 0) {
      test.skip(true, "No properties in seed data — cannot test detail highlight")
      return
    }

    await propertyLinks.first().click()
    await page.waitForLoadState("networkidle")

    expect(page.url()).toMatch(/\/real-estate\/[0-9a-f-]+$/)

    const link = page.locator("nav a").filter({ hasText: /^Real Estate$/ })
    const style = await link.getAttribute("style")
    expect(style).toContain("var(--nav-active-bg)")
  })
})
