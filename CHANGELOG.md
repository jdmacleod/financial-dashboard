# Changelog

All notable changes to HearthLedger are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.9.1.0] - 2026-06-20

### Added

- **Phase 9 wealth dashboard — full UI redesign** across seven screens:
  - **Overview tab** — rebuilt with a 4-KPI row (net worth, assets, liabilities, cash-flow MTD), a range-controlled net-worth trend chart (YTD / 1Y / All), an allocation donut, top-spending categories, and a budget alerts row.
  - **Accounts tab** — split-panel ledger with category groups (Assets / Liabilities) in the left pane and an account detail panel on the right; Edit button opens a modal for nickname, institution, notes.
  - **Investments tab** — brokerage accounts with per-account balance history line charts and snapshot-based balance display.
  - **Retirement tab** — tax-treatment groupings (Tax-deferred / Tax-free / Guaranteed) with KPI row showing total, tax-deferred, and tax-free subtotals.
  - **Real estate tab** — property cards with equity bar, YoY delta, and latest valuation date.
  - **Cash flow tab** — 4-KPI row (income, expenses, net, savings rate), 12-month bar chart, and spending breakdown by category.
  - **Sidebar shell** — persistent navigation with SVG icons, design tokens, and dark/light/system mode toggle.
- **EditAccountModal** — inline edit for account nickname, institution name, and notes (encrypted at rest); accessible keyboard-trap modal with overlay-click and Escape dismissal.
- **Design tokens** — complete migration to CSS custom-property design system (`--bg`, `--card`, `--bd`, `--text`, `--text2`, `--muted`, `--up`, `--liab`, etc.) across all pages.
- **Notes field exposed on AccountResponse** — `notes` is now decrypted and returned in GET /accounts so the dashboard can display and edit account notes without a separate call.

### Changed

- **Overview widget order** — Liabilities card now appears before the Largest Holdings card, matching the net-worth calculation flow (assets − liabilities = net worth).
- **Snapshot prefetch** — Retirement, Investments, and Assets pages prefetch all visible account snapshots in a single `useQueries` batch on mount, eliminating the N+1 waterfall where each row fired a sequential request.
- **Range toggle routing** — replaced `window.history.replaceState + synthetic PopStateEvent` with `useNavigate()` from TanStack Router; `range` is now a validated search param on the layout route so all child routes inherit it.

### Fixed

- **compactCurrency negative values** — the dashboard KPI compact formatter now correctly renders negative values (e.g., `−$12k`) by prepending the sign and using `Math.abs`.
- **Retirement prefetch scope** — snapshot prefetch in the Retirement page was accidentally fetching all accounts; it now filters to retirement account types only.
- **notes max-length validation** — `AccountCreate.notes` and `AccountUpdate.notes` now enforce `max_length=2000` via Pydantic `Field`, preventing unbounded input at the API boundary.
- **Range param allowlist** — the range URL param is now validated against `["ytd", "1y", "all"]` before use; invalid values silently fall back to `"ytd"`.

## [0.9.0.1] - 2026-06-19

### Fixed

- **Transaction dialogs** — all four native `<dialog>` elements (Add transaction, Edit transaction, Import, Delete confirm) now carry `aria-labelledby` wired to their heading, satisfying WCAG 2.1 SC 4.1.2 for modal landmark labeling.
- **Pension account empty state** — the transaction list empty state for pension accounts was incorrectly showing an Import CTA; it now shows the same "Add your first entry" call-to-action as investment accounts, consistent with Import being hidden in the header for pension accounts.
- **Amount sign-toggle on empty input** — clicking the ± toggle before entering an amount was writing `"-"` to the RHF field, which passed `min(1)` validation but failed `parseFloat`, surfacing a confusing "Amount must be a valid number" error instead of "Amount is required"; the toggle now skips `field.onChange` when the field is empty.

### Changed

- **Add transaction modal** — default sign is now expense (`−`), so the majority-expense use case requires no extra click. Payees with income can toggle to `+` before entering the amount.
- **Edit transaction modal** — sign toggle initialises from the stored transaction sign, so editing an income entry preserves the `+` rather than defaulting to expense.

## [0.9.0.0] - 2026-06-19

### Added

- **Assets page** — new dedicated page for valuation-based accounts (Real Estate, Pensions, Investments) accessible from the main nav. Each section shows balances from the appropriate source: property valuations for real estate, estimated present value for pensions, and manual snapshot balances for investment accounts.
- **Update value modal** — investment and HSA accounts now have an "Update value" button that creates a balance snapshot for any date, keeping your net worth current without transaction import.
- **Pension present value display** — the Assets page computes and displays an estimated present value for each pension using a simplified perpetuity formula (monthly benefit × 12 / 4% discount rate), so pensions contribute meaningfully to your asset picture.
- **Household name as dashboard title** — the Dashboard page heading now shows your household name instead of the generic "Dashboard" label.

### Changed

- **Accounts page now focuses on transaction accounts** — checking, savings, and other liquid assets only. Real estate, pension, and investment accounts moved to the new Assets page, reducing clutter for households with many account types.
- **Net worth now includes pension present value** — the FIRE and net worth time-series calculations account for pension PV, giving a more complete picture of total household wealth.
- **Real estate balances in account list come from property valuations** — `GET /accounts` now reads real estate balances from the latest property valuation batch rather than the snapshot table, keeping the account list accurate without manual updates.

### Fixed

- **Account list loads faster** — snapshot queries for non-real-estate accounts are now batched into a single `DISTINCT ON` query instead of one query per account, eliminating the N+1 fan-out that slowed down the Accounts page for households with many accounts.

## [0.8.0.0] - 2026-06-19

### Added

- **Net worth breakdown panel** — stacked area sub-chart below the net worth trend on
  the Reports page showing how checking/savings, investment, retirement, real estate,
  HSA, and liabilities compose your net worth over the same period.
- **Property edit modal** — edit address, property type, purchase date, purchase price,
  and linked mortgage directly from the Property Detail page without navigating away.
- **Property gain/loss header** — Property Detail page now shows absolute gain/loss and
  percentage return (e.g. "+$80,000 · +26.7%") computed server-side with full Decimal
  precision. Absolute gain still shows for properties with a $0 purchase price (inherited,
  gifted) even when percentage is undefined.
- **Member role management** — primary members can promote or demote household members
  via a two-step confirmation flow; promoting to primary shows a confirmation banner
  before the mutation fires to prevent accidental promotions.
- **Property type in account creation** — choose Primary Residence, Rental, Vacation,
  Commercial, Land, or Other when adding a Real Estate account; address is now required
  at creation time to match the edit modal's validation.

### Fixed

- **Real estate values in net worth** — property estimated values now flow into the net
  worth calculation correctly; previously they were always counted as $0.
- **Deterministic property valuations** — the batch valuation query now uses
  `ROW_NUMBER()` partitioned by property instead of a max-date JOIN, preventing
  non-deterministic net worth figures when two valuations share the same date.

### Changed

- Net worth report time-series now batches real estate property valuations per time
  point (one query per month-end instead of two queries per property per month-end),
  eliminating the N×2 query fan-out for households with multiple properties.

---

## [0.7.0.0] - 2026-06-18

### Added

- **Pension accounts** — new `pension` account type tracks defined-benefit pension plans.
  Add plan name, administrator, monthly benefit estimate, eligibility age or date, COLA
  adjustment rate, vesting status, survivor benefit percentage, and notes. Data is
  AES-256-GCM encrypted at rest.
- **Pension detail page** — dedicated edit form at `/accounts/{id}/pension` with inline
  editing of all pension fields; vested/unvested badge; blank state with "Add pension
  details" prompt.
- **Pension info on Transactions page** — defined-benefit summary card shown above the
  transaction list for pension accounts, showing plan name, monthly benefit, eligibility,
  and vested status. "Add pension details →" link when no record exists.
- **Property type selection** — choose the property type (Primary Residence, Rental,
  Vacation, Commercial, Land, Other) when adding a Real Estate account; value stored in
  database and shown throughout the UI.
- **Property info banner on Transactions page** — real estate accounts show a banner with
  property address and a "Track this property →" link to the Property Detail page.
- **`GET /accounts/{id}/property` endpoint** — fetch the property record for a real
  estate account by account ID, enabling direct navigation from account context to
  property detail.
- **FIRE pension income streams** — FIRE detect automatically creates an income stream
  for each vested pension with a non-zero benefit estimate. Streams include eligibility
  year, COLA rate, and member attribution.
- **Net Worth report pension annotations** — pension accounts appear below the net worth
  chart with annual benefit, eligibility info, and a "Show PV" toggle that converts annual
  benefit to present value using a 4% discount rate.

### Fixed

- Equity calculation now uses `abs(mortgage_balance)` so mortgages stored as negative
  balances compute correct equity instead of inflating it.
- `PATCH /properties/{id}` no longer crashes with 500 when `property_type: null` is
  sent explicitly — null is now treated as "no change".
- `PATCH /accounts/{id}/pension` no longer crashes with 500 when `is_vested: null` is
  sent explicitly — null is now treated as "no change".
- Migration 0004 now grants `SELECT, INSERT, UPDATE, DELETE` on `pension_accounts` to
  the application role, preventing `permission denied` errors on first deploy.

---

## [0.6.0.0] - 2026-06-18

### Added

- **Backup service** — scheduled ARQ task (`run_backup`) performs `pg_dump` daily
  at 2am, AES-256-GCM encrypts the dump, verifies integrity by decrypting to
  `/dev/null`, then prunes backups older than `BACKUP_RETENTION_DAYS`. Manual
  trigger via `POST /api/v1/backups`; download via `GET /api/v1/backups/{id}/download`.
  Encrypted `.dump.enc` files use the same `SECRET_ENCRYPTION_KEY` as field
  encryption. Backup jobs older than the retention window are pruned automatically.
- **Settings > Backups page** — summary bar with last-backup timestamp and size;
  amber warning banner when the most recent successful backup is more than 48 hours
  old; "Run backup now" button with spinner; paginated backup history table with
  Download button; collapsible "How to restore" CLI instructions.
- **Real estate valuation refresh** — `refresh_valuations` ARQ task runs weekly
  (Monday 3am); supports ATTOM Data and Estated providers; API failures are caught
  and logged per-property without interrupting the rest of the run. The last known
  value is used in net worth calculations when a provider is unavailable.
- **Property detail valuation UI** — current value card with source badge
  (`Manual · Jan 10` / `ATTOM · Jan 14`) and confidence score; "Update manually"
  modal with date picker; valuation history chart with source color-coding.
- **Settings > Properties panel** — valuation provider selector (Manual / ATTOM /
  Estated), API key input, "Test connection" button, "Last refresh" timestamp per
  property.
- **Dashboard widget customization** — drag-to-reorder and show/hide per widget,
  stored in `household_members.settings` JSONB (per-member, not household-wide).
  Persists across page reloads. Six widgets: Net Worth, Cash Flow MTD, Spending by
  Category, Budget Alerts, Account Balances, Recent Transactions. "Reset to default"
  button.
- **Dark mode** — Tailwind `dark:` class toggle; three modes (Light / Dark / System);
  system follows `prefers-color-scheme`; toggle stored in `localStorage`; all
  shadcn/ui components and Recharts charts render with theme-aware colors via
  `useThemeColors()` hook. Settings > Appearance toggle.
- **Import history page** (`/settings/imports`) — table of all past import jobs
  with account nickname, filename, format badge (CSV/OFX/QFX), status badge, records
  imported/skipped counts, triggered-by user, and expandable error message for failed
  imports. Filterable by account and date range.

---

## [0.5.0.0] - 2026-06-18

### Added

- **PDF summary export** — generates a multi-section WeasyPrint PDF with cover
  page, net worth snapshot (account numbers masked to last 4 digits), cash flow
  summary, top-10 spending categories, budget vs actuals, and investment account
  list. Download via `GET /api/v1/exports/{id}/download`.
- **PDF executor export** — full-detail PDF including decrypted account numbers,
  routing numbers, institution names, real estate holdings (decrypted addresses),
  debt schedule with payoff estimates, FIRE scenario snapshot, and an audit
  summary page ("generated by [name] on [datetime]"). Requires re-authentication
  and primary role.
- **Excel summary workbook** — 7-sheet openpyxl workbook (Net Worth History,
  Account Directory, Transactions, Budget vs Actuals, Spending by Category, Debt
  Schedule, FIRE Projections). All sheets have bold headers, `$#,##0.00` monetary
  formatting, ISO 8601 dates, and alternating row shading. Transactions sheet has
  auto-filter enabled on all columns.
- **Excel executor workbook** — same as summary but with full decrypted account
  numbers, routing numbers, and institution names in the Account Directory and
  Debt Schedule sheets.
- **Re-authentication gate** — executor exports (`pdf_executor`,
  `excel_executor`) require a valid `X-Reauth-Token` header issued by
  `POST /api/v1/auth/reauth`. Tokens are single-use: consumed on first use
  and invalidated in Redis for the 10-minute TTL. Partners are rejected
  regardless of token.
- **Export job API** — `POST /api/v1/exports` enqueues an ARQ background job
  and returns `export_job_id`; `GET /api/v1/exports/{id}` polls status
  (`pending → processing → complete | failed`); `GET /api/v1/exports/{id}/download`
  streams the generated file with correct `Content-Type` and
  `Content-Disposition: attachment` headers; `GET /api/v1/exports` lists
  the 30 most recent export jobs for the household.
- **Export audit events** — each successful export writes an
  `export.generated` event to the audit log with `export_type`, `anonymized`,
  date range, and filename. No encrypted field values are written.
- **Export modal** — two-step frontend flow: configure (format selector with
  four cards, date range, account filter) → re-authenticate for executor types
  → generating spinner with 2-second polling → download button on complete.
  Executor cards are disabled for partner users with a "Primary members only"
  label.
- **Export history page** (`/settings/exports`) — table of recent exports with
  type badge, date range, generator, timestamp, and Download button. Executor
  exports show a lock icon.

---

## [0.4.0.0] - 2026-06-18

### Added

- **FIRE scenario modeling** — create and manage FIRE scenarios with target
  annual spend, safe withdrawal rate, expected return, inflation rate, and
  optional target retirement age. Full CRUD via `GET/POST/PATCH/DELETE
/api/v1/fire-scenarios`.
- **Auto-detect income streams** — `POST /api/v1/fire-scenarios/{id}/detect`
  analyzes the trailing 12 months of transaction data to identify income streams
  by category, estimate annual gross income and expenses, compute savings rate,
  and snapshot the current portfolio value. Re-running detection merges results
  without duplicating streams; manually-overridden amounts are preserved.
- **Income stream editor** — add, edit, and remove income streams on each FIRE
  scenario. Streams have a type (salary, rental, consulting, pension, Social
  Security, investment, other), annual amount, growth rate, start/end year, and
  a pre- vs. post-retirement flag for supplemental income after FIRE.
- **FIRE projection engine** — `GET /api/v1/fire-scenarios/{id}/projection`
  runs a year-by-year compound projection of portfolio value vs. the FIRE
  number (target spend ÷ SWR). Returns per-year breakdown (portfolio, income,
  spend, savings, effective withdrawal) and a summary with FIRE year, FIRE age,
  years-to-FIRE, and a human-readable headline ("FIRE in 14 years at age 52").
  Post-retirement supplemental income streams correctly reduce effective
  withdrawal rather than savings.
- **Debt payoff projector** — `GET /api/v1/debt-payoff` computes both
  avalanche (highest interest rate first) and snowball (lowest balance first)
  strategies side by side. When a debt reaches zero, its minimum payment rolls
  into the extra payment for the next target. Returns total interest paid,
  months to payoff, payoff date, and payoff order for each strategy.
- **FIRE pages** — `/fire` lists all scenarios with headline metrics; `/fire/{id}`
  shows a two-panel layout with the scenario editor on the left and a portfolio
  projection chart on the right. Auto-detect button populates income streams
  from transaction history with a spinner and detection-warning banners.
- **Debt page** — `/debt` lists all debts with current balance, interest rate,
  minimum payment, and projected payoff date. Extra monthly payment input
  updates both strategy projections in real time. Side-by-side avalanche vs.
  snowball comparison shows total interest saved and a stacked-area balance
  chart.

---

## [0.3.0.0] - 2026-06-18

### Added

- **Net worth over time** — `GET /api/v1/reports/net-worth` returns a monthly,
  quarterly, or annual series with per-account-type breakdown (checking/savings,
  investment, retirement, real estate, HSA, liabilities). Accounts with no
  snapshots fall back to running transaction balance automatically.
- **Cash flow report** — `GET /api/v1/reports/cash-flow` returns income vs.
  expenses by month or quarter with savings rate per period. Transfer transactions
  are excluded from both sides of the ledger.
- **Spending by category** — `GET /api/v1/reports/spending-by-category` with
  optional `parent_category_id` drilldown; uncategorized transactions grouped
  separately; sorted by spend descending.
- **Budget management** — full CRUD for `Budget` records: set a monthly/annual
  amount per category with `effective_from`/`effective_to` date ranges so budgets
  can change over time without losing history.
- **Budget vs actuals** — `GET /api/v1/reports/budget-vs-actuals?month=YYYY-MM`
  matches each category to the most recent effective budget row, computes
  `actual`, `remaining`, and `percentage_used`.
- **Property P&L** — `GET /api/v1/reports/property-pnl` aggregates income and
  expense transactions tagged to a real-estate property; returns gross income, net
  income, net yield %, expense breakdown by category, and a monthly series.
- **Dashboard** — `GET /api/v1/dashboard` aggregates net worth (with 30-day
  change), MTD cash flow, top-5 spending categories, budget alerts (>90% used),
  and total assets/liabilities into a single endpoint — loads from one request.
- **Audit log API** — `GET /api/v1/audit-log` with filtering by `entity_type`,
  `entity_id`, `user_id`, date range, and pagination. Access control: primary
  members see all events; partners/dependents may only query per-record history
  for entities they can see; auth events show own events for all users.
- **Activity log page** (`/settings/activity`) — chronological audit event feed
  for primary members; filterable by member, entity type, and date. Human-readable
  event descriptions generated client-side from `action` + context fields.
- **Security log page** (`/settings/security`) — auth event feed accessible to
  all users (own events only); primary sees all users' auth events.
- **Per-record history panel** — collapsible History section on transaction detail
  and account detail pages, queries
  `GET /api/v1/audit-log?entity_type=transaction&entity_id={id}`, rendered
  oldest-first as a timeline.

### Changed

- Dashboard homepage replaced with metric cards (net worth, MTD income/expenses,
  savings rate) + 12-month net worth line chart + spending donut chart + budget
  alert chips.
- `/reports/net-worth` page: date range picker, monthly/quarterly/annual toggle,
  stacked area breakdown chart.
- `/reports/cash-flow` page: grouped bar chart with net overlay, month-by-month
  table with savings rate column.
- `/reports/spending` page: donut chart + ranked list with category drilldown;
  custom date range selector.
- `/budgets` page: budget list grouped by category with inline progress bars;
  current month selector; "Add budget" modal.
- `/properties/{id}` now has two tabs — Valuation history (line chart + manual
  update button) and P&L (date range, gross/net cards, expense breakdown,
  monthly series table).

---

## [0.2.0.0] - 2026-06-18

### Added

- **CSV import** — upload a bank export, map columns interactively (preview 10
  rows, confirm mapping), and import in the background via ARQ worker; duplicate
  rows are silently skipped by `external_id` exact match or fuzzy payee+date+amount
  match (>80% similarity)
- **OFX/QFX import** — drag-and-drop an OFX or QFX file; fields map automatically
  (`FITID`→`external_id`, `DTUSER`→`transaction_date`, `TRNAMT`→`amount`,
  `NAME`→`payee_raw`, `MEMO`→`memo`), no column-mapping step required
- **Transfer detection** — pairs of transactions in different accounts with equal
  and opposite amounts within a 3-day window are automatically linked
  (`is_transfer = true`, shared `transfer_pair_id`) and excluded from income/expense
  totals
- **Import job tracking** — `GET /api/v1/import-jobs/{id}` polls job status;
  frontend polls every 2 s and shows final counts ("Imported N, skipped M duplicates")
- **Category management** — create, rename, and delete custom categories; system
  categories (Income, Expenses, Transfer, …) are protected from edit or deletion
- **Balance snapshots** — manually record point-in-time balances for any account,
  with optional `contributed_ytd`, `employer_match_ytd`, and memo fields
- **Bulk categorize** — select multiple transactions and apply a category in one
  operation; each transaction receives its own audit event
- **Property tag** — transactions can be linked to a real-estate property via
  `real_estate_property_id`; the field is returned in responses and filterable via
  `GET /api/v1/accounts/{id}/transactions?real_estate_property_id=…`
- **Debit/credit split columns** — CSV importer accepts separate Debit and Credit
  columns; combined as `amount = credit − debit`

### Changed

- Category badge on transaction list is now clickable inline — selecting a new
  category immediately PATCHes the transaction and marks it reviewed
- Import modal supports a full four-step flow: file pick → column mapping
  (CSV only) → confirmation → live progress indicator

### Fixed

- **Dependency updates** — updated all runtime and toolchain dependencies for
  security and compatibility: uvicorn 0.49, SQLAlchemy 2.0.51, pydantic 2.13.4,
  python-jose 3.5.0, passlib 1.7.4, fastapi 0.137.2, ruff 0.15.18,
  Recharts 3, Redis 8, Node 26, PostgreSQL 18; `bcrypt<4.1` pin preserved
  to prevent passlib self-test crash

---

## [0.1.0.0] - 2026-06-18

### Added

- **Manual transaction entry** — create transactions directly from the Transactions page without importing a file. A "New entry" button opens a date/amount/payee/memo/category form with full validation.
- **Edit transactions** — click the pencil icon on any transaction row to open a pre-filled edit form. Changes to date, amount, payee, memo, and category are saved via PATCH and reflected immediately.
- **Delete transactions** — click the trash icon on any transaction row to open a confirmation dialog before deleting. Failed deletes surface an inline error so the dialog stays open rather than disappearing silently.
- **Smart category defaults** — retirement account types (401k, 403b, IRA, Roth IRA) pre-select "Contributions"; pension accounts pre-select "Income"; other account types leave the field blank.
- **Investment account empty state** — accounts that are investment-type show a focused "No transactions recorded yet" CTA instead of the import-first message.
- **Backend startup script** — `backend/start.sh` runs Alembic migrations before starting the server, so Docker deployments self-migrate on first boot.

### For contributors

- **Shared account type constants** — `RETIREMENT_ACCOUNT_TYPES` and `INVESTMENT_ACCOUNT_TYPES` extracted to `src/lib/accountTypes.ts` for use across components.
- **Vitest test suite** — 27 frontend tests covering modal rendering, validation, API success/error paths, category defaults, empty states, and modal interaction flows.

### Fixed

- `TransactionUpdate` backend schema now includes `transaction_date` and `memo` — previously these fields were accepted by the frontend edit form but silently ignored by the backend.
- `EditTransactionModal` memo field correctly sends `null` to clear a memo (not empty string) using Pydantic's `model_fields_set` to distinguish "not provided" from "explicitly set to null".
