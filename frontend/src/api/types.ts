export interface TokenResponse {
  access_token: string
  token_type: string
  must_change_password?: boolean
}

export interface UserResponse {
  id: string
  member_id: string | null
  email: string
  is_active: boolean
  last_login: string | null
  created_at: string
}

export interface ProvisionResponse {
  member: MemberResponse
  user: UserResponse
  temporary_password: string
}

export interface TemporaryPasswordResponse {
  temporary_password: string
}

export type FilingStatus =
  | "single"
  | "married_filing_jointly"
  | "married_filing_separately"
  | "head_of_household"
  | "qualifying_surviving_spouse"

export interface HouseholdResponse {
  id: string
  name: string
  settings: Record<string, unknown>
  filing_status: FilingStatus | null
  state: string | null
  created_at: string
}

export interface HouseholdUpdate {
  name?: string
  filing_status?: FilingStatus | null
  state?: string | null
}

export interface MemberResponse {
  id: string
  household_id: string
  display_name: string
  role: "primary" | "partner" | "dependent"
  date_of_birth: string | null
  retirement_target_age: number | null
  is_active: boolean
  settings: Record<string, unknown>
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
  | "heloc"
  | "student_loan"
  | "other_asset"
  | "other_liability"

export type TaxTreatment = "pretax" | "roth" | "taxable"

export interface AccountResponse {
  id: string
  nickname: string
  account_type: AccountType
  owner_member_id: string | null
  ownership_entity_id: string | null
  institution_name: string | null
  account_number_last4: string | null
  include_in_net_worth: boolean
  tax_treatment: TaxTreatment | null
  is_active: boolean
  current_balance: string | null
  balance_as_of: string | null
  notes: string | null
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

export interface TransactionCreate {
  transaction_date: string
  amount: string
  payee_normalized: string
  memo?: string
  category_id?: string | null
  // is_transfer intentionally omitted from forms — backend defaults to false
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

export type BackupTrigger = "manual" | "scheduled"
export type BackupStatus = "pending" | "processing" | "complete" | "failed"

export interface BackupJobResponse {
  id: string
  triggered_by: BackupTrigger
  triggered_by_user_id: string | null
  status: BackupStatus
  filename: string | null
  file_size_bytes: number | null
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface ApiError {
  detail: string | Record<string, unknown>
}

export type BudgetPeriod = "monthly" | "quarterly" | "annual"

export interface SnapshotResponse {
  id: string
  account_id: string
  snapshot_date: string
  balance: string
  contributed_ytd: string | null
  employer_match_ytd: string | null
  memo: string | null
  source: string
  created_at: string
}

export interface BudgetResponse {
  id: string
  household_id: string
  category_id: string
  period: BudgetPeriod
  amount: string
  effective_from: string
  effective_to: string | null
}

export type ValuationSource = "manual" | "api_attom" | "api_estated"
export type PropertyType =
  | "primary_residence"
  | "rental"
  | "vacation"
  | "commercial"
  | "land"
  | "other"

export interface PropertyResponse {
  id: string
  account_id: string
  nickname: string
  address: string
  purchase_date: string | null
  purchase_price: string | null
  linked_mortgage_account_id: string | null
  ownership_entity_id: string | null
  property_type: PropertyType
  current_estimated_value: string | null
  current_value_as_of: string | null
  gain_loss: string | null
  gain_loss_pct: string | null
  created_at: string
  updated_at: string
}

export interface PropertyEquityResponse {
  property_value: string
  valuation_date: string
  valuation_source: string
  mortgage_balance: string | null
  mortgage_balance_as_of: string | null
  mortgage_balance_visible: boolean
  equity: string | null
}

export interface PensionAccountResponse {
  id: string
  account_id: string
  member_id: string | null
  plan_name: string | null
  administrator: string | null
  monthly_benefit_estimate: string | null
  eligibility_age: number | null
  eligibility_date: string | null
  cola_adjustment_rate: string
  is_vested: boolean
  vesting_date: string | null
  survivor_benefit_percent: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PensionAccountCreate {
  member_id?: string | null
  plan_name?: string | null
  administrator?: string | null
  monthly_benefit_estimate?: string | null
  eligibility_age?: number | null
  eligibility_date?: string | null
  cola_adjustment_rate?: string
  is_vested?: boolean
  vesting_date?: string | null
  survivor_benefit_percent?: string | null
  notes?: string | null
}

export interface PensionAccountUpdate {
  member_id?: string | null
  plan_name?: string | null
  administrator?: string | null
  monthly_benefit_estimate?: string | null
  eligibility_age?: number | null
  eligibility_date?: string | null
  cola_adjustment_rate?: string | null
  is_vested?: boolean | null
  vesting_date?: string | null
  survivor_benefit_percent?: string | null
  notes?: string | null
}

export interface ValuationResponse {
  id: string
  real_estate_property_id: string
  valuation_date: string
  estimated_value: string
  source: ValuationSource
  confidence_score: string | null
  created_at: string
}

export interface NetWorthBreakdown {
  checking_savings: string
  investment: string
  retirement: string
  real_estate: string
  hsa: string
  other_assets: string
  mortgage: string
  other_liabilities: string
}

export interface NetWorthPoint {
  date: string
  total_assets: string
  total_liabilities: string
  net_worth: string
  breakdown: NetWorthBreakdown
}

export interface PensionAnnotation {
  account_id: string
  nickname: string
  monthly_benefit: string | null
  eligibility_age: number | null
  eligibility_date: string | null
  estimated_pv: string | null
}

export interface NetWorthReport {
  series: NetWorthPoint[]
  current: NetWorthPoint | null
  pension_annotations: PensionAnnotation[]
}

export interface CashFlowPeriod {
  period: string
  income: string
  expenses: string
  net: string
  savings_rate: number
}

export interface RetirementIncomeBreakdown {
  social_security: string
  pension: string
  rmd: string
  total: string
  has_data: boolean
}

export interface CashFlowReport {
  series: CashFlowPeriod[]
  totals: CashFlowPeriod
  retirement_income: RetirementIncomeBreakdown
}

export interface SpendingCategoryItem {
  category_id: string | null
  name: string
  amount: string
  percentage: number
  transaction_count: number
  has_children: boolean
}

export interface SpendingByCategoryReport {
  total: string
  categories: SpendingCategoryItem[]
}

export interface BudgetVsActualsItem {
  category_id: string
  name: string
  budget: string
  actual: string
  remaining: string
  percentage_used: number
  period: BudgetPeriod
}

export interface BudgetVsActualsReport {
  period: string
  categories: BudgetVsActualsItem[]
}

export interface BudgetTrendPoint {
  period: string
  budget: string
  actual: string
  variance: string
}

export interface BudgetTrendReport {
  series: BudgetTrendPoint[]
  total_budget: string
  total_actual: string
  total_variance: string
}

export interface SavingsRatePoint {
  period: string
  income: string
  expenses: string
  savings: string
  savings_rate: number
  rolling_rate: number
}

export interface SavingsRateReport {
  series: SavingsRatePoint[]
  average_rate: number
  best_period: string | null
  worst_period: string | null
}

export interface MemberRequiredDistribution {
  member_id: string
  display_name: string
  date_of_birth: string | null
  current_age: number | null
  rmd_start_age: number | null
  rmd_start_year: number | null
  has_started: boolean
  pretax_balance: string | null
  balance_as_of: string | null
  divisor: string | null
  rmd_amount: string | null
  note: string | null
}

export interface RequiredDistributionsReport {
  year: number
  members: MemberRequiredDistribution[]
}

export interface MilestoneItem {
  key: string
  label: string
  age_label: string
  date: string
  year: number
  reached: boolean
}

export interface MemberMilestones {
  member_id: string
  display_name: string
  date_of_birth: string | null
  current_age: number | null
  milestones: MilestoneItem[]
  note: string | null
}

export interface AgeMilestonesReport {
  members: MemberMilestones[]
}

export interface PropertyExpenseItem {
  category_id: string | null
  name: string
  amount: string
}

export interface PropertyMonthlyPoint {
  period: string
  income: string
  expenses: string
  net: string
}

export interface PropertyPnLReport {
  property_id: string
  nickname: string
  address: string
  period: { from: string; to: string }
  gross_income: string
  total_expenses: string
  net_income: string
  net_yield_pct: number | null
  expense_breakdown: PropertyExpenseItem[]
  monthly_series: PropertyMonthlyPoint[]
}

export interface EstateExposureEntity {
  entity_id: string | null
  entity_name: string | null
  entity_type: string | null
  is_in_taxable_estate: boolean
  assets: string
  liabilities: string
  net_value: string
}

export interface EstateExposureReport {
  as_of: string
  gross_taxable_estate: string
  excluded_from_estate: string
  total_net_worth: string
  exemption_per_person: string
  exemption_holders: number
  applicable_exemption: string
  taxable_overage: string
  estimated_federal_estate_tax: string
  federal_estate_tax_rate: number
  entities: EstateExposureEntity[]
}

export interface DashboardNetWorth {
  current: string
  change_30d: string
  change_30d_pct: number | null
}

export interface DashboardCashFlow {
  income: string
  expenses: string
  net: string
}

export interface DashboardSpendingCategory {
  category_id: string | null
  name: string
  amount: string
}

export interface DashboardBudgetAlert {
  category: string
  used_pct: number
}

export interface DashboardAccountsSummary {
  total_assets: string
  total_liabilities: string
}

export interface DashboardResponse {
  net_worth: DashboardNetWorth
  cash_flow_mtd: DashboardCashFlow
  top_spending_categories: DashboardSpendingCategory[]
  budget_alerts: DashboardBudgetAlert[]
  accounts_summary: DashboardAccountsSummary
}

export interface AuditLogEntryResponse {
  id: string
  action: string
  entity_type: string
  entity_id: string | null
  previous_value: Record<string, unknown> | null
  new_value: Record<string, unknown> | null
  user_id: string | null
  user_display_name: string | null
  context: Record<string, unknown>
  ip_address: string | null
  created_at: string
}

export interface PaginatedAuditLog {
  items: AuditLogEntryResponse[]
  page: number
  page_size: number
  total: number
}

// ---- FIRE Modeling ----

export type IncomeStreamType =
  | "salary"
  | "rental"
  | "consulting"
  | "pension"
  | "social_security"
  | "investment"
  | "other"

export interface IncomeStream {
  id: string
  label: string
  type: IncomeStreamType
  amount_annual: string
  growth_rate_annual: string
  start_year: number
  end_year: number | null
  is_pre_retirement: boolean
  notes: string | null
  real_estate_property_id: string | null
  source_account_id: string | null
  auto_detected: boolean
  detected_at: string | null
}

export interface FireScenarioResponse {
  id: string
  household_id: string
  member_id: string | null
  name: string
  target_annual_spend: string
  safe_withdrawal_rate: string
  expected_annual_return: string
  expected_inflation_rate: string
  target_retirement_age: number | null
  additional_income_streams: IncomeStream[]
  detected_annual_income: string | null
  detected_annual_expenses: string | null
  detected_savings_rate: string | null
  detected_portfolio_value: string | null
  detection_trailing_months: number
  detected_at: string | null
  created_at: string
  updated_at: string
}

export interface FireDetectionResponse {
  scenario: FireScenarioResponse
  warnings: string[]
}

export interface YearProjectionResponse {
  year: number
  age: number | null
  portfolio: string
  annual_income: string
  annual_spend: string
  annual_savings: string
  supplemental_income: string
  effective_withdrawal: string
  fire_number: string
  is_fire_year: boolean
  required_distribution: string
}

export interface FireProjectionSummary {
  fire_year: number | null
  fire_age: number | null
  years_to_fire: number | null
  fire_number: string
  headline: string
}

export interface FireProjectionResponse {
  summary: FireProjectionSummary
  projections: YearProjectionResponse[]
}

// ---- Debt Payoff ----

export interface DebtWithAccountResponse {
  debt_id: string
  account_id: string
  nickname: string
  current_balance: string
  interest_rate: string
  minimum_payment: string
}

export interface DebtPayoffMonthResponse {
  month: number
  date: string
  total_remaining: string
  per_debt: Record<string, string>
}

export interface DebtPayoffPlanResponse {
  strategy: string
  months_to_payoff: number
  total_interest_paid: string
  payoff_date: string
  monthly_series: DebtPayoffMonthResponse[]
  payoff_order: string[]
}

export interface DebtPayoffComparisonResponse {
  debts: DebtWithAccountResponse[]
  avalanche: DebtPayoffPlanResponse
  snowball: DebtPayoffPlanResponse
}

// ---- Exports ----

export type ExportType = "pdf_summary" | "pdf_executor" | "excel_summary" | "excel_executor"
export type ExportJobStatus = "pending" | "processing" | "complete" | "failed"

export interface ExportJobResponse {
  id: string
  household_id: string
  export_type: ExportType
  anonymized: boolean
  parameters: Record<string, unknown>
  status: ExportJobStatus
  filename: string | null
  error_message: string | null
  generated_by: string
  created_at: string
  completed_at: string | null
}

export interface ExportCreateResponse {
  export_job_id: string
}

// ── Demo-data extension (read API) ──────────────────────────────────────────

export interface AdvisoryNoteResponse {
  id: string
  household_id: string
  account_id: string | null
  ownership_entity_id: string | null
  category: string
  title: string
  body: string
  created_at: string
}

export interface OwnershipEntityResponse {
  id: string
  household_id: string
  entity_type: string
  name: string
  grantor_member_id: string | null
  is_in_taxable_estate: boolean
  counts_in_personal_net_worth: boolean
  created_at: string
}

export interface InsurancePolicyResponse {
  id: string
  household_id: string
  policy_type: string
  insured_member_id: string | null
  owner_ownership_entity_id: string | null
  coverage_amount: string
  premium_amount: string
  premium_cadence: string
  cash_value_account_id: string | null
  carrier: string | null
  policy_number: string | null
  technical_notes: string | null
  insured_real_estate_id: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface VestingEventResponse {
  id: string
  equity_grant_id: string
  event_date: string
  shares_vested: string
  fmv_at_event: string
  taxable_ordinary_income: string
  amt_preference_amount: string | null
  shares_sold_to_cover: string
  resulting_lot_id: string | null
  created_at: string
}

export interface EquityGrantResponse {
  id: string
  household_id: string
  member_id: string
  grant_type: string
  grant_date: string
  shares_granted: string
  strike_price: string | null
  ticker: string
  vesting_schedule: Record<string, unknown>
  espp_discount_pct: string | null
  espp_lookback: boolean | null
  created_at: string
  vesting_events: VestingEventResponse[]
}

export interface InvestmentLotResponse {
  id: string
  account_id: string
  ticker: string
  shares: string
  basis_per_share: string
  acquired_date: string
  basis_type: string
  asset_class: string | null
  created_at: string
}

export interface PositionRollup {
  ticker: string
  shares: string
  cost_basis: string
  lot_count: number
}

export interface HoldingsMixSlice {
  asset_class: string
  cost_basis: string
  percentage: number
}

export interface PositionsSummary {
  positions: PositionRollup[]
  holdings_mix: HoldingsMixSlice[]
  total_cost_basis: string
}

export interface CapitalCommitmentResponse {
  id: string
  household_id: string
  fund_name: string
  committed_amount: string
  called_to_date: string
  nav_account_id: string
  vintage_year: number
  created_at: string
}
