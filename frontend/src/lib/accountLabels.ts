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
  student_loan: "Student Loan",
  other_asset: "Other Asset",
  other_liability: "Other Liability",
}

export const PROPERTY_TYPE_LABELS: Record<string, string> = {
  primary_residence: "Primary Residence",
  rental: "Rental Property",
  vacation: "Vacation Home",
  commercial: "Commercial",
  land: "Land",
  other: "Other",
}
