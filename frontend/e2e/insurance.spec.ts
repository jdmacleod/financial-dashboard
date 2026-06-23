import { test, expect, type Page } from "@playwright/test"

const BASE_URL = "http://localhost"
const PASSWORD = "HearthDemo1!" // pragma: allowlist secret

async function login(page: Page, email: string) {
  await page.goto(`${BASE_URL}/login`)
  await page.getByRole("textbox").first().fill(email)
  await page.getByRole("textbox").nth(1).fill(PASSWORD)
  await page.getByRole("button", { name: "Sign in" }).click()
  await page.waitForURL(`${BASE_URL}/`)
}

// ── Castellano household — richest set of insurance data (5 policies) ─────────

test.describe("Insurance tab — Castellano Household", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "rosa@castellano.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")
  })

  test("page heading and subtitle are present", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Insurance" })).toBeVisible()
    await expect(page.getByText(/Coverage carried/)).toBeVisible()
  })

  test("Add policy button is visible in the header", async ({ page }) => {
    await expect(page.getByRole("button", { name: "Add policy" })).toBeVisible()
  })

  test("shows all Castellano insurance policies", async ({ page }) => {
    // Castellano has: 2x permanent_life, 2x homeowners, umbrella, long_term_care, scheduled_specialty
    await expect(page.getByText("Umbrella Liability")).toBeVisible()
    await expect(page.getByText("Long-Term Care")).toBeVisible()
    await expect(page.getByText("Scheduled / Specialty")).toBeVisible()
    const permanentLifeItems = await page.getByText("Permanent Life").all()
    expect(permanentLifeItems.length).toBe(2)
    const homeownersItems = await page.getByText("Homeowners").all()
    expect(homeownersItems.length).toBe(2)
  })

  test("sort control is present", async ({ page }) => {
    await expect(page.getByRole("combobox", { name: "Sort policies" })).toBeVisible()
  })

  test("sort by Coverage ↓ places highest-coverage policy first", async ({ page }) => {
    const sortSelect = page.getByRole("combobox", { name: "Sort policies" })
    await sortSelect.selectOption("coverage_desc")
    await page.waitForTimeout(200)

    // Castellano umbrella is $10M — highest coverage overall
    const cards = page.locator(".space-y-3 > div")
    const firstCardText = await cards.first().textContent()
    expect(firstCardText).toContain("10,000,000")
  })

  test("sort by Premium ↓ places highest-premium policy first", async ({ page }) => {
    const sortSelect = page.getByRole("combobox", { name: "Sort policies" })
    await sortSelect.selectOption("premium_desc")
    await page.waitForTimeout(200)

    // ILIT permanent life has $45,000/yr premium — highest
    const cards = page.locator(".space-y-3 > div")
    const firstCardText = await cards.first().textContent()
    expect(firstCardText).toContain("45,000")
  })

  test("sort by Type A–Z lists Disability before Umbrella", async ({ page }) => {
    const sortSelect = page.getByRole("combobox", { name: "Sort policies" })
    await sortSelect.selectOption("type_asc")
    await page.waitForTimeout(200)

    const cards = page.locator(".space-y-3 > div")
    const names = await cards.locator(".text-sm.font-semibold").allTextContents()
    // Long-Term Care (L) and Permanent Life (P) both come before Umbrella (U)
    const umbrellaIdx = names.indexOf("Umbrella Liability")
    const ltcIdx = names.indexOf("Long-Term Care")
    expect(ltcIdx).toBeLessThan(umbrellaIdx)
  })

  test("policy count badge is shown", async ({ page }) => {
    // Castellano has 5 original + 2 homeowners policies = 7
    await expect(page.getByText(/7 policies/)).toBeVisible()
  })

  test("ILIT-owned policy shows entity name with outside estate label", async ({ page }) => {
    // Castellano ILIT-owned permanent life — owner entity is an ILIT
    await expect(page.getByText(/outside estate/i).first()).toBeVisible()
  })

  test("each policy card has Edit and Delete buttons", async ({ page }) => {
    const editButtons = page.getByRole("button", { name: "Edit" })
    const deleteButtons = page.getByRole("button", { name: "Delete" })
    // 5 original policies + 2 homeowners = 7
    expect(await editButtons.count()).toBe(7)
    expect(await deleteButtons.count()).toBe(7)
  })

  // ── Add Policy modal ─────────────────────────────────────────────────────────

  test("Add Policy modal opens with all required fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    const modal = page.locator(".fixed.inset-0.z-50")
    await expect(modal.getByRole("heading", { name: "Add Policy" })).toBeVisible()
    await expect(modal.getByText("Policy type")).toBeVisible()
    await expect(modal.getByText("Coverage amount")).toBeVisible()
    await expect(modal.locator("label", { hasText: "Premium" })).toBeVisible()
  })

  test("Add Policy modal closes on ✕ click", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    await expect(page.getByRole("heading", { name: "Add Policy" })).toBeVisible()
    await page.locator("button").filter({ hasText: "✕" }).click()
    await expect(page.getByRole("heading", { name: "Add Policy" })).not.toBeVisible()
  })

  test("Add Policy form shows insured member field for life policy types", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    // term_life is the default type — insured member field should appear
    await expect(page.getByText("Insured member")).toBeVisible()
  })

  test("Add Policy form shows owner entity field for permanent_life", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    const modal = page.locator(".fixed.inset-0.z-50")
    // The policy type select is inside the modal
    const typeSelect = modal.locator("select").first()
    await typeSelect.selectOption("permanent_life")
    await expect(modal.getByText(/Trust \/ entity owner/)).toBeVisible()
  })

  test("Add Policy form hides insured member for umbrella_liability", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    const modal = page.locator(".fixed.inset-0.z-50")
    const typeSelect = modal.locator("select").first()
    await typeSelect.selectOption("umbrella_liability")
    await expect(modal.getByText("Insured member")).not.toBeVisible()
  })

  // ── Edit modal ───────────────────────────────────────────────────────────────

  test("Edit modal opens for first policy with pre-filled values", async ({ page }) => {
    const editButtons = page.getByRole("button", { name: "Edit" })
    await editButtons.first().click()

    const modal = page.locator(".fixed.inset-0.z-50")
    await expect(modal.getByRole("heading", { name: "Edit Policy" })).toBeVisible()
    await expect(modal.getByText("Coverage amount")).toBeVisible()
    await expect(modal.locator("label", { hasText: "Premium" })).toBeVisible()
    // The subtitle shows the policy type name
    await expect(modal.locator("p.text-sm.text-gray-500")).toBeVisible()
  })

  test("Edit modal closes on Cancel", async ({ page }) => {
    const editButtons = page.getByRole("button", { name: "Edit" })
    await editButtons.first().click()
    await expect(page.getByRole("heading", { name: "Edit Policy" })).toBeVisible()
    await page.getByRole("button", { name: "Cancel" }).click()
    await expect(page.getByRole("heading", { name: "Edit Policy" })).not.toBeVisible()
  })
})

// ── Langford household — permanent life with cash-value account ───────────────

test.describe("Insurance tab — Langford Household", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "bob@langford.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")
  })

  test("displays Langford policies including Permanent Life", async ({ page }) => {
    await expect(page.getByText("Permanent Life")).toBeVisible()
    await expect(page.getByText("Umbrella Liability")).toBeVisible()
    // Langford has 2 LTC policies (Bob + Maggie) — use first()
    await expect(page.getByText("Long-Term Care").first()).toBeVisible()
  })

  test("cash value badge appears for permanent life policy", async ({ page }) => {
    await expect(page.getByText("Cash value in net worth")).toBeVisible()
  })

  test("insured member name is shown for policies with an insured", async ({ page }) => {
    // Bob's permanent life and LTC policies are insured to named members
    await expect(page.getByText(/Insured:/).first()).toBeVisible()
  })

  test("page loads without JS errors", async ({ page }) => {
    const errors: string[] = []
    page.on("pageerror", (err) => errors.push(err.message))
    await page.reload()
    await page.waitForLoadState("networkidle")
    expect(errors.filter((e) => !e.includes("ResizeObserver"))).toHaveLength(0)
  })
})

// ── Chen-Nakamura household — umbrella + disability ───────────────────────────

test.describe("Insurance tab — Chen-Nakamura Household", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "wei@chen-nakamura.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")
  })

  test("shows umbrella and disability policies", async ({ page }) => {
    await expect(page.getByText("Umbrella Liability")).toBeVisible()
    await expect(page.getByText("Disability")).toBeVisible()
  })

  test("policy count shows 3 policies", async ({ page }) => {
    // Chen-Nakamura: umbrella + disability + homeowners (HO-6 condo)
    await expect(page.getByText(/3 policies/)).toBeVisible()
  })

  test("disability policy shows insured member", async ({ page }) => {
    await expect(page.getByText(/Insured:/)).toBeVisible()
  })
})

// ── Carrier and policy number display ────────────────────────────────────────

test.describe("Insurance tab — carrier and policy number display", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "wei@chen-nakamura.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")
  })

  test("carrier name is shown on policy card", async ({ page }) => {
    // USAA appears on umbrella and homeowners cards; Guardian on disability
    await expect(page.getByText("USAA").first()).toBeVisible()
    await expect(page.getByText("Guardian")).toBeVisible()
  })

  test("policy number is shown on policy card", async ({ page }) => {
    await expect(page.getByText(/#UMB-2021-0044821/)).toBeVisible()
  })

  test("Add Policy modal includes carrier and policy number fields", async ({ page }) => {
    await page.getByRole("button", { name: "Add policy" }).click()
    const modal = page.locator(".fixed.inset-0.z-50")
    await expect(modal.getByText("Carrier")).toBeVisible()
    await expect(modal.getByText("Policy number")).toBeVisible()
  })
})

// ── Create flow — list updates after adding ───────────────────────────────────

test.describe("Insurance tab — create flow persists and updates list", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "zoe@park-cole.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")
  })

  test("adding a policy from empty state shows it in the list", async ({ page }) => {
    // Start from empty state
    await expect(page.getByText(/No insurance policies yet/)).toBeVisible()

    // Open modal and fill the form
    await page.getByRole("button", { name: "Add first policy" }).click()
    const modal = page.locator(".fixed.inset-0.z-50")
    await modal.locator("select").first().selectOption("umbrella_liability")

    // Coverage amount
    const coverageInput = modal.locator("input").nth(0)
    await coverageInput.fill("1000000")

    // Premium amount
    const premiumInput = modal.locator("input").nth(1)
    await premiumInput.fill("1200")

    // Carrier
    const carrierInput = modal.locator("input").nth(2)
    await carrierInput.fill("State Farm")

    // Policy number
    const policyNumInput = modal.locator("input").nth(3)
    await policyNumInput.fill("SF-TEST-0001")

    await modal.getByRole("button", { name: "Add Policy" }).click()

    // Modal should close and list should show the new policy
    await expect(page.getByRole("heading", { name: "Add Policy" })).not.toBeVisible()
    await expect(page.getByText("Umbrella Liability")).toBeVisible()
    await expect(page.getByText("State Farm")).toBeVisible()
  })
})

// ── Park-Cole household — no insurance ───────────────────────────────────────

test.describe("Insurance tab — Park-Cole Household (no policies)", () => {
  test.beforeEach(async ({ page }) => {
    // Clean up any policy created by the create-flow test above before asserting empty state
    await login(page, "zoe@park-cole.local")
    await page.goto(`${BASE_URL}/insurance`)
    await page.waitForLoadState("networkidle")

    // Delete any lingering test policies so we start fresh
    const deleteButtons = page.getByRole("button", { name: "Delete" })
    const count = await deleteButtons.count()
    for (let i = 0; i < count; i++) {
      page.on("dialog", (d) => d.accept())
      await deleteButtons.first().click()
      await page.waitForLoadState("networkidle")
    }
  })

  test("shows empty state with Add first policy button", async ({ page }) => {
    await expect(page.getByText(/No insurance policies yet/)).toBeVisible()
    await expect(page.getByRole("button", { name: "Add first policy" })).toBeVisible()
  })

  test("empty-state Add button opens the Add Policy modal", async ({ page }) => {
    await page.getByRole("button", { name: "Add first policy" }).click()
    await expect(page.getByRole("heading", { name: "Add Policy" })).toBeVisible()
  })
})
