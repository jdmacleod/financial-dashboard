export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface HouseholdResponse {
  id: string
  name: string
  settings: Record<string, unknown>
  created_at: string
}

export interface MemberResponse {
  id: string
  household_id: string
  display_name: string
  role: "primary" | "partner" | "dependent"
  date_of_birth: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserResponse {
  id: string
  member_id: string | null
  email: string
  is_active: boolean
  last_login: string | null
  created_at: string
}

export type AccountType =
  | "checking"
  | "savings"
  | "credit_card"
  | "investment_brokerage"
  | "retirement_401k"
  | "retirement_403b"
  | "retirement_ira"
  | "retirement_roth_ira"
  | "pension"
  | "hsa"
  | "real_estate"
  | "mortgage"
  | "auto_loan"
  | "personal_loan"
  | "student_loan"
  | "other_asset"
  | "other_liability"

export interface AccountResponse {
  id: string
  nickname: string
  account_type: AccountType
  owner_member_id: string | null
  institution_name: string | null
  account_number_last4: string | null
  include_in_net_worth: boolean
  is_active: boolean
  current_balance: string | null
  balance_as_of: string | null
  created_at: string
  updated_at: string
}

export interface AccessGrantResponse {
  id: string
  account_id: string
  owner_member_id: string
  grantee_member_id: string
  access_level: string
  is_active: boolean
  created_at: string
}

export interface CategoryResponse {
  id: string
  household_id: string
  name: string
  parent_category_id: string | null
  color_hex: string
  icon: string | null
  is_income: boolean
  is_system: boolean
  created_at: string
}

export interface TransactionResponse {
  id: string
  account_id: string
  real_estate_property_id: string | null
  transaction_date: string
  post_date: string | null
  amount: string
  payee_raw: string | null
  payee_normalized: string | null
  memo: string | null
  category_id: string | null
  is_transfer: boolean
  transfer_pair_id: string | null
  tags: string[]
  source: string
  import_job_id: string | null
  external_id: string | null
  is_reviewed: boolean
  created_at: string
  updated_at: string
}

export interface PaginatedTransactions {
  items: TransactionResponse[]
  total: number
  page: number
  page_size: number
}

export type ImportFormat = "csv" | "ofx" | "qfx"
export type ImportJobStatus = "pending" | "processing" | "complete" | "failed"

export interface ImportPreviewResponse {
  headers: string[]
  preview_rows: string[][]
  suggested_mapping: Record<string, string>
}

export interface ImportJobResponse {
  id: string
  account_id: string
  filename: string
  format: ImportFormat
  status: ImportJobStatus
  records_found: number | null
  records_imported: number | null
  records_skipped: number | null
  error_message: string | null
  imported_by: string
  created_at: string
  updated_at: string
}

export interface ApiError {
  detail: string | Record<string, unknown>
}
