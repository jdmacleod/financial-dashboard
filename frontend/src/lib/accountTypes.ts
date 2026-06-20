import type { AccountType } from "@/api/types"

export const RETIREMENT_ACCOUNT_TYPES: AccountType[] = [
  "retirement_401k",
  "retirement_403b",
  "retirement_ira",
  "retirement_roth_ira",
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
