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

// Color dots per account category group (used in Accounts split-panel ledger)
export const ACCOUNT_CATEGORY_COLORS: Record<string, string> = {
  "Banking & Cash": "#46b888",
  Retirement: "#d9b96a",
  Investments: "#6c97c4",
  "Real estate": "#a9743f",
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
