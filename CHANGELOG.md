# Changelog

All notable changes to HearthLedger are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
