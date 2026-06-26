import type { AccountType } from "@/api/types"

export const ACCOUNT_LABELS: Record<AccountType, string> = {
  checking: "Checking",
  savings: "Savings",
  credit_card: "Credit Card",
  investment_brokerage: "Brokerage",
  retirement_401k: "401(k)",
  retirement_403b: "403(b)",
  retirement_ira: "IRA",
  retirement_roth_ira: "Roth IRA",
  pension: "Pension",
  hsa: "HSA",
  real_estate: "Real Estate",
  mortgage: "Mortgage",
  auto_loan: "Auto Loan",
  personal_loan: "Personal Loan",
  heloc: "HELOC",
  student_loan: "Student Loan",
  other_asset: "Other Asset",
  other_liability: "Other Liability",
}

// Canonical order of asset/liability categories across the whole app. The
// sidebar nav, the Accounts page groups, the Dashboard allocation donut, and the
// Net Worth breakdown panel all sort by this rank so they never drift apart
// (they used to disagree three ways). Order: liquid cash first, then taxable
// investments, real estate, tax-advantaged retirement, then HSA / other assets,
// with liabilities last. Matches the sidebar's Investments → Real Estate →
// Retirement ordering.
export const ASSET_CATEGORY_ORDER = [
  "banking",
  "investments",
  "real_estate",
  "retirement",
  "hsa",
  "other_assets",
  "liabilities",
] as const

export type AssetCategoryKey = (typeof ASSET_CATEGORY_ORDER)[number]

// Sort rank for a canonical category key; unknown keys sort last (stable).
export function assetCategoryRank(key: AssetCategoryKey): number {
  const i = ASSET_CATEGORY_ORDER.indexOf(key)
  return i === -1 ? ASSET_CATEGORY_ORDER.length : i
}

// Color dots per account category group (used in Accounts split-panel ledger)
export const ACCOUNT_CATEGORY_COLORS: Record<string, string> = {
  "Banking & Cash": "#46b888",
  Retirement: "#d9b96a",
  Investments: "#6c97c4",
  "Real Estate": "#a9743f",
  Liabilities: "#e0b48a",
}

export const PROPERTY_TYPE_LABELS: Record<string, string> = {
  primary_residence: "Primary Residence",
  rental: "Rental Property",
  vacation: "Vacation Home",
  commercial: "Commercial",
  land: "Land",
  other: "Other",
}
