# Changelog

All notable changes to HearthLedger are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
