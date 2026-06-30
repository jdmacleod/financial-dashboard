import type { AccountType } from "@/api/types"

export const RETIREMENT_ACCOUNT_TYPES: AccountType[] = [
  "retirement_401k",
  "retirement_403b",
  "retirement_ira",
  "retirement_roth_ira",
  "hsa",
]

export const BROKERAGE_ACCOUNT_TYPES: AccountType[] = ["investment_brokerage"]

export const INVESTMENT_ACCOUNT_TYPES: AccountType[] = [
  "retirement_401k",
  "retirement_403b",
  "retirement_ira",
  "retirement_roth_ira",
  "investment_brokerage",
  "pension",
]

// Mirrors backend app.db.models.account.TRANSACTION_BASED_TYPES. These accounts
// derive their balance from the running sum of transactions, so an opening
// balance is recorded as a transaction. Everything else (investments,
// retirement) uses point-in-time snapshots instead.
export const TRANSACTION_BASED_ACCOUNT_TYPES: AccountType[] = [
  "checking",
  "savings",
  "credit_card",
  "mortgage",
  "auto_loan",
  "personal_loan",
  "heloc",
  "student_loan",
  "other_asset",
  "other_liability",
  "sbloc",
  "margin",
]
