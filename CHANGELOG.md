# Changelog

All notable changes to HearthLedger are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.20.1.0] - 2026-06-24

### Fixed

- **Lines of credit always value from their actual balance.** SBLOC and margin accounts are now treated as transaction-tracked liabilities, so their net-worth value follows draws and paydowns over time and can never be pinned to a single static figure. As part of this, any transaction-tracked liability (credit cards, lines of credit, loans) that was imported as a balance snapshot with no transaction history now reports that snapshot balance instead of zero. No change to the sample data.

## [0.20.0.0] - 2026-06-24

### Added

- **Reports section in the sidebar.** Net Worth, Spending, Savings Rate, and Budget Trend now live together in a dedicated "Reports" group in the left sidebar, promoted out of the user-settings dropdown where they were harder to find. The dropdown no longer carries report links.

### Changed

- **Sidebar ordering by time horizon.** The main navigation now reads Overview → Accounts → Cash Flow → Investments → Real Estate → Retirement, moving the monthly Cash Flow view up and the long-horizon Retirement view to the bottom. The Planning section reorders to Budgets → Debt → FIRE → Insurance → Estate → Insights, shortest action horizon first.

### Fixed

- **Real Estate stays highlighted on property pages.** Viewing a property detail page now keeps the "Real Estate" sidebar item highlighted. The property detail route moved from `/properties/:id` to `/real-estate/:id` so the active-state matching works; any old `/properties/...` bookmarks will no longer resolve.

## [0.19.0.0] - 2026-06-24

### Added

- **Savings Rate report.** A new report (`/reports/savings-rate`) charts the share of income you keep each month — (income − expenses) ÷ income — with a trailing 3-month rolling average, your average rate over the window, and your best and leanest months. Savings rate is the single biggest lever on time to financial independence, and it now has a dedicated view instead of being buried in the Cash Flow numbers.
- **Budget Trend report.** A new report (`/reports/budget-trend`) plots total budgeted vs actual spend each month with a variance line, plus totals showing whether you came in over or under budget across the window. It complements the per-category Budgets tab with a whole-household trend.

### Fixed

- **Net worth liabilities now reflect loan paydowns.** Liabilities backed by a structured debt record (student loans, auto loans) were shown at a single static balance across the entire net-worth history, so the liabilities line never moved as payments posted and net worth was understated. Transaction-tracked consumer loans are now valued from their running balance at each date, so the liabilities line amortizes correctly month over month.
- **Park-Cole sample data.** Corrected the Park-Cole household's stored loan balances so the Debt page and the Net Worth report agree (the auto loan now reads paid-off, and the student-loan balances match their transaction history).

### Changed

- **Spending donut.** The category legend no longer crowds and clips the donut chart. The donut is larger and centered, the total spend is shown in the center, and the category list on the right serves as the legend.

## [0.18.0.0] - 2026-06-24

### Added

- **Category hierarchy.** Categories now have a two-level parent/child tree. The Categories page shows collapsible parent groups with color dots (click to open the native color picker); system categories show a SYSTEM badge and allow color edits only; custom categories get Rename and Delete at both parent and child level.
- **Category slugs.** Each system category gets a stable machine-readable slug (e.g. `social_security_income`, `pension_income`) stored in a new `slug` column with a partial unique index. Slugs drive the retirement-income breakdown in the Cash Flow report (replacing fragile name matching) and enable reliable cross-installation lookups.
- **Category colors.** System parent categories now seed with distinct colors (income green, housing blue, healthcare purple, etc.). Child categories default to `#888888`. The Alembic migration 0013 backfills slugs and colors for existing installations.
- **Colored category bars in Cash Flow.** The top-spending-categories panel now fills each horizontal bar with the category's `color_hex`. Each bar is a button that navigates to `/reports/spending?category=<id>` for drill-through, with hover/focus styles and an aria-label. A "View full breakdown →" link appears below the panel.
- **Dynamic category colors in Spending Report.** Pie chart slices and breakdown progress bars now use each category's `color_hex` (fetched from the categories API) instead of a static color rotation.
- **URL-driven drill-down in Spending Report.** Opening `/reports/spending?category=<id>` pre-selects that category's drill-down view, so Cash Flow bar clicks land in the correct context.
- **Grouped `<optgroup>` selectors.** Category dropdowns in TransactionForm, the inline CategoryBadge select, and the bulk-categorize select now group children under their parent with an `{parent} — general` option at the top of each group.
- **Mobile-responsive Cash Flow report.** KPI grid switches from 4 columns to 2×2 on narrow viewports; the bottom panel stack collapses to a single column.

## [0.17.0.0] - 2026-06-23

### Added

- **Sort and filter on the Budgets tab.** A filter bar below the donut chart lets you narrow both Budget vs Actuals and All Budgets by category name simultaneously. A "X of Y" count badge tracks how many actuals match. Each section has its own sort control: Budget vs Actuals sorts by % used (default), budget amount, actual spend, or name; All Budgets sorts by name (default), budget amount, or period.

### Fixed

- YTD range now anchors to the selected month's year rather than the current calendar year, so navigating to a prior month and switching to YTD shows data for that year's January through the selected month.
- Budget amount of zero is now rejected in the Add and Edit forms instead of silently creating a budget that can never trigger an over-budget alert.

## [0.16.0.0] - 2026-06-23

### Added

- **Budgets range toggle.** Switch the Budgets tab between Month, YTD, 1Y, and All views. Range modes aggregate budget vs actuals across all months in parallel — the donut chart and totals update as each month loads.
- **Budget donut chart.** A new visual overview shows top spending categories as a proportional donut, with a legend and total budgeted / spent / % used summary. Renders above the budget-vs-actuals list.
- **Annual budget support.** Budgets can now be marked as annual. The backend prorates annual amounts to a monthly equivalent (÷12) in budget vs actuals reports. The "annual÷12" indicator appears on budget rows when viewing a single month.
- **Full budget edit modal.** The inline amount-only editor is replaced by a full modal that lets you change the category, period (monthly / annual), amount, effective from date, and effective to date.

### Fixed

- Month navigation arrows (Previous / Next) no longer drift by one day in negative UTC-offset timezones due to UTC-midnight date parsing.
- Parallel month fetch errors now surface a disclosure banner instead of silently showing incomplete totals.
- Budget-vs-actuals query is now deterministic when two budgets for the same category share an `effective_from` date (stable `ORDER BY effective_from DESC, id DESC`).
- The `month` query parameter for budget-vs-actuals now rejects out-of-range month values (e.g. `2024-00`, `2024-13`) with a 422 instead of a 500.
- Negative budget amounts are now rejected at the API layer with a 422 instead of reaching the database as an integrity error.

## [0.15.0.0] - 2026-06-22

### Added

- **Investment positions.** The Investments page now rolls your cost-basis lots up into a "Top positions" table (per-ticker shares and total cost basis) and a "Holdings mix" donut broken out by asset class. Backed by a new `GET /investment-positions` endpoint. Lots can carry an asset class, and the demo households classify common tickers so the mix is meaningful out of the box. Cost basis is shown rather than market value — HearthLedger tracks no live prices.
- **Retirement income breakdown.** The cash-flow report now splits retirement income into labeled buckets — Social Security, pension, and required minimum distributions — shown as a panel that hides itself for households not yet drawing those benefits.
- **Pension estimates keep their history.** Editing a pension's benefit estimate no longer rewrites past net-worth chart points: each point is valued from the estimate that was in effect on that date. Existing pensions are backfilled automatically.

### Changed

- **More accurate pension present value.** Net worth now values a defined-benefit pension as a finite life annuity that accounts for the years until eligibility, COLA growth, and the survivor benefit — replacing the old flat "annual benefit ÷ 4%" perpetuity. The net-worth report surfaces this value directly instead of recomputing it in the browser.

### Fixed

- The Assets page no longer risks a crash when showing equity for a cash-purchased property that has no linked mortgage.

## [0.14.0.0] - 2026-06-22

### Added

- **One-action "Add person".** A primary or partner can now add a login-capable household member in a single step from the Members page. HearthLedger generates a temporary password, shows it once with a copy button and a "shown once" reminder (and a regenerate option), and the new person sets their own password the first time they sign in. No email or SMTP required. Only a primary can add another primary.
- **Forced first-login password reset.** A member who signs in with a temporary password is taken straight to a "set your password" screen that blocks the rest of the app until they choose their own.

### Changed

- The "Add member" action on the Members page is now "Add person" and creates the member together with their sign-in, replacing the previous member-only dialog. (The member-only API endpoint is unchanged.)

## [0.13.0.0] - 2026-06-22

### Added

- **Estate-exposure report.** A new panel on the Insights page shows your gross taxable estate versus the applicable federal exemption (one per primary/partner, capped at two for portability), how much sits over the exemption, the estimated federal estate tax, and a per-titling breakdown of which holdings are inside the estate versus sheltered in an ILIT or irrevocable trust. Backed by a new `GET /reports/estate-exposure` endpoint. The panel hides itself for households with nothing to show.
- **Manage planning data, not just view it.** Full create / update / delete endpoints for ownership entities (trusts), advisory notes, insurance policies, equity grants, cost-basis lots, and private-fund capital commitments. Encrypted names round-trip correctly and never appear in the audit log; edits are role-gated and audited.
- **Richer demo households.** Non-qualified stock options and an inherited IRA (Park-Cole), a mega-backdoor Roth overlay (Chen-Nakamura), sandwich-generation eldercare support (Okonkwo-Rivera), and a brokerage margin loan (Whitfield-Torres).
- **Trust badges** on accounts and properties titled to an ownership entity, so you can see at a glance what's held in a trust.
- **Insights filters and polish.** Category filter chips with per-category icons, emphasis styling for concentration and scope notes, and a top-notes teaser card on the Dashboard.
- **Contributor guide.** A new `CONTRIBUTING.md` covering dev setup, the required `pre-commit install`, and an optional pre-push hook that runs the full test suites.

### Changed

- **Advisory notes respect account visibility.** A note anchored to an account is only shown to members who can see that account; household- and trust-level notes remain visible to everyone.

### Fixed

- The audit-log snapshot no longer fails on the insurance policy's `metadata` field, which collided with an internal name.
- Resetting or deleting demo data no longer fails on account access-grant foreign keys.

## [0.12.0.0] - 2026-06-22

### Added

- **Frontend for the demo-data extension.** The new read endpoints now have UI surfaces, all under a "Planning" nav group:
  - **Insights page** (`/insights`) — advisory notes grouped by category (Estate, Tax, Concentration, Insurance, Retirement, Charitable, Scope & Omissions).
  - **Estate & structure page** (`/estate`) — ownership entities (trusts) with plain-language flags for net-worth inclusion and taxable-estate status, plus each entity's anchored advisory notes.
  - **Insurance page** (`/insurance`) — policies with coverage, premium cadence, and trust-owned / cash-value-in-net-worth flags.
  - **Investments page panels** — equity grants (with vesting-event counts, vested income, and an AMT flag on held ISO tranches), cost-basis lots (incl. inherited step-up), and private-fund commitments (called-of-committed progress). Each renders only when the household has the data.
  - **Anchored advisory notes** — a reusable panel surfaces account- or entity-anchored notes inline on the per-account Transactions page and on each Estate entity.
- **Typed read-API client + response types** for all six demo-data endpoints (advisory notes, ownership entities, insurance policies, equity grants, investment lots, capital commitments).

## [0.11.0.0] - 2026-06-22

### Added

- **Read API for the demo-data extension tables (Option B read path).** Household-scoped, JWT-visibility-gated read endpoints that surface the new structures in-app:
  - `GET /api/v1/advisory-notes` — with `?account_id`, `?ownership_entity_id`, `?category` filters.
  - `GET /api/v1/ownership-entities` — decrypts `name_enc` at read time; ciphertext never leaves the service.
  - `GET /api/v1/insurance-policies` — exposes policy `metadata`.
  - `GET /api/v1/equity-grants` (optional `?member_id`) — each grant carries its vesting events embedded.
  - `GET /api/v1/investment-lots` (optional `?account_id`) — visibility-enforced through `AccountRepository.get_visible`, so a member only sees lots in accounts they can see.
  - `GET /api/v1/capital-commitments` — decrypts `fund_name_enc` at read time.

### Fixed

- **FIRE detector ignored the demo-extension account types.** `fire_detector.py` now counts `treasury`, `inherited_ira`, and `private_fund` in the portfolio + asset base, `life_insurance_cash_value` as an asset, and `sbloc`/`margin` as revolving liabilities resolved via the transaction-sum path (they carry no snapshots). Net-worth reporting already respected these; FIRE detection (`detected_portfolio_value`, net worth) now does too — correcting H5 and H6 projections.

## [0.10.0.0] - 2026-06-22

### Added

- **Demo-data extension schema (migration 0007)** — seven new tables that the demo dataset could not previously express, wired into the existing visibility, `@audit`, encryption, and net-worth machinery:
  - `ownership_entity` (trust/titling layer), `insurance_policy`, `equity_grant` + `vesting_event`, `investment_lot` (cost basis), `capital_commitment` (private funds), `advisory_note`.
  - `account_type` enum extended with `inherited_ira`, `sbloc`, `margin`, `private_fund`, `life_insurance_cash_value`, `treasury`; `accounts` gains `ownership_entity_id` + `is_revolving`; `real_estate_properties` gains `ownership_entity_id`. Reversible downgrade (verified upgrade->downgrade->upgrade round-trip).
- **Ownership-entity-aware net worth** — `ReportService` and the FIRE input detector exclude assets titled in entities flagged `counts_in_personal_net_worth = false` (ILIT/CRT/DAF-held), while revocable-trust titling stays in net worth. New asset/liability account types added to the net-worth buckets.
- **Thin `@audit` service methods** — `EquityCompService.record_vesting_event` (atomic lot + income + sell-to-cover transfer), `PrivateFundService.record_capital_call`, `CreditLineService.record_sbloc_draw`/`record_sbloc_interest`. Encrypted `ownership_entity.name_enc` and `capital_commitment.fund_name_enc` are excluded from audit-log payloads.
- **Demo household H6 Castellano** (Scarsdale, NY) — `--household 6` (or `--household all`) seeds the dataset's only single-member household (~$18.29M net worth): widowed single filer, degenerate RBAC (one principal, zero access grants), revocable trust + ILIT + CRT + DAF, legacy concentrated stock with a 2022 inherited-stepup lot, inherited IRA on the SECURE 10-year clock, private-equity capital commitment with calls, revolving SBLOC, full decumulation income, and combined federal + New York estate-cliff exposure.
- **Shared taxonomy additions** — equity/investment income categories, `qcd_note` (RMD-satisfying, income-excluded), new `insurance` and `interest_expense` parents with premium/SBLOC leaves, `private_school_tuition`, and transfer categories for equity sales, capital flows, trust/charitable funding, gifting, Roth conversions, and 529 superfunding.
- **Scope-boundaries documentation** — `~/Documents/hearthledger-spec/docs/scope-boundaries.md` records the ~$20M ceiling and the five intentional omissions; `scope_omission` advisory notes seeded on H3 and H6. New `docs/hearthledger-demo-data-coverage-matrix.md` and `docs/hearthledger-demo-data-implementation-plan.md`.

### Changed

- **Households H1-H5 revised** with equity compensation (ESPP/RSU/ISO), concentration + cost-basis lots, revocable trusts, insurance-as-asset (umbrella/disability/LTC/permanent life), charitable vehicles (DAF/QCD), backdoor and conversion Roth flows, SBLOC borrowing, and 22 advisory notes across the set.
- **Per-household summary net worth reconciled to `ReportService`** as of end-of-window (2026-06-21). The prior summary literals were hand-estimates that never matched the app's own net-worth report; all six now match exactly. Published figures: H1 ~$1,003,300, H2 ~$3,620,400, H3 ~$10,019,300, H4 ~$246,000, H5 ~$13,327,100, H6 $18,290,000.

### Fixed

- **`frontend/package.json` version drift** — bumped from a stale `0.9.3.0` to track the VERSION file.

## [0.9.4.0] - 2026-06-21

### Added

- **Demo households H4 Park-Cole and H5 Langford** — `--household 4` and `--household 5` (or `--household all`) now seed two additional fictitious households, extending the demo dataset to five complete households:
  - **H4 Park-Cole** (Nashville, TN) — Late-20s renters; 2 members, 13 accounts, ~$154K starting net worth. Exercises: Honda Accord auto-loan payoff cascade (Aug 2025), cascaded student-loan increase, dual Roth IRA contributions, HSA, biweekly payroll with third-paycheck months, renters insurance, FIRE scenario targeting independence at 45.
  - **H5 Langford** (Sarasota, FL) — Retirees; 2 members, 15 accounts, 2 real estate properties, ~$12.9M net worth. Exercises: Social Security income (3rd-Wednesday disbursement), pension income, IRA Required Minimum Distribution (SECURE 2.0 age-73 rule, quarterly withdrawals 2025–2026), Maggie's LLC consulting draw, ACA marketplace premium (stepped 2024→2025→2026), Medicare Part B/D/Medigap, Sarasota primary home (cash purchase — no linked mortgage), Highlands NC vacation home with mortgage, two FIRE scenarios (portfolio sustainability + longevity stress test).
- **`SEED_DATE_END` environment variable** — Seed scripts now respect `SEED_DATE_END=YYYY-MM-DD` to extend the transaction window beyond the default 2026-06-21 cutoff. Documented in `.env.example`.
- **`third_wednesday()` helper in `_util.py`** — Returns the 3rd Wednesday of any month, clamped to `DATE_END`; used for Bob Langford's Social Security deposit scheduling.
- **`home_property_tax` category** — New category under Housing for primary-residence property taxes, distinct from `rental_property_tax` (rental/vacation property expenses).
- **Additive seeding guard** — `seed_demo_data.py` now checks per-household existence instead of a global check, enabling H4/H5 to be seeded onto a database that already contains H1–H3 without skipping or re-inserting.
- **`delete`, `reset`, and `inspect` actions for `seed_demo_data.py`** — the seed script now supports `--action delete` (remove household + all cascaded data), `--action reset` (delete then reseed atomically per household), and `--action inspect` (read-only summary of DB state). All destructive actions require `[y/N]` confirmation unless `--yes` is passed.
- **Phase 11 design doc** — `docs/phase-11-demo-households-h4-h5.md` documents the household specifications, account structure, income patterns, debt payoff schedules, and FIRE scenario parameters.

### Fixed

- **Budget amounts for H1/H2/H3 seed households** — corrected several budget line amounts that were off by a factor of 10x or misallocated across categories; net worth totals and category spend patterns now match design spec.
- **H5 Langford advisory fees and home insurance budgets** — `advisory_fees` and `home_insurance` monthly budget values were swapped; corrected to match the Phase 11 spec.
- **`users.member_id` FK changed to `ON DELETE CASCADE`** — previously `SET NULL`, which orphaned user rows when a household member was deleted; cascade ensures user accounts are removed with their member.
- **IncomeStreamType for brokerage dividend streams** — Langford brokerage dividend income streams were incorrectly typed as `interest`; corrected to `investment` so they appear in the right projection bucket.

### Added (tests)

- **`backend/tests/unit/test_seed_util.py`** — expanded to 33 unit tests covering all pure-function helpers in `_util.py` (`third_wednesday`, `jitter`, `clamp_day`, `gen_variable`, `last_day_of`, `all_months`, `friday_dates`, `rand_date`) and the H5-specific `_split` function in `h5_langford.py`.
- **`backend/tests/unit/test_seed_demo_data.py`** — 4 unit tests for `_confirm()` covering the `--yes` bypass flag and `y`/`n`/empty interactive responses.

## [0.9.3.0] - 2026-06-20

### Added

- **Context-aware "+" buttons on Accounts page** — clicking "+" in the Banking & Cash group opens `AddAccountModal` filtered to checking/savings/other_asset types; clicking in the Liabilities group shows only liability types; clicking in Retirement, Investments, or Real estate navigates to the dedicated page (`/reports/retirement`, `/reports/investments`, `/assets`) where those account types are managed. The header "+ Add account" button retains the full list of transaction account types.
- **Phase 8/9/10 documentation** — `docs/phase-8-accounts-assets.md`, `docs/phase-9-wealth-dashboard.md`, and `docs/phase-10-ux-completeness.md` created; `docs/README.md` updated to include all phases.

### Fixed

- **VERSION file drift** — `VERSION` was stuck at 0.9.0.0 while `backend/pyproject.toml` and `frontend/package.json` had advanced to 0.9.2.1; synced to 0.9.2.1 then bumped to 0.9.3.0 as part of this release.
- **Accounts.test.tsx router mock** — `@tanstack/react-router` mock now exports `useNavigate`, preventing all 21 existing Accounts tests from failing after `useNavigate` was added to `Accounts.tsx`.

## [0.9.2.1] - 2026-06-20

### Fixed

- **ORM model drift** — `FireScenario.member_id` was missing its `ForeignKey('household_members.id', ondelete='SET NULL')` declaration and `__table_args__` partial index, causing Alembic autogenerate to see drift versus migration 0005.
- **FIRE projection DOB** — `FireScenarioService.project()` always used the primary member's date of birth even when `member_id` was set; it now looks up the attributed member's DOB and falls back to the primary member only when `member_id` is null.
- **net_worth() N+1 queries** — `net_worth()` series loop issued one SQL query per transaction-based account (credit_card/heloc) per date point; refactored to batch all such sums in one query per date point via `txn_sums` dict passed through `_net_worth_point` → `_liability_value_at`.
- **fire_detector net worth date cap** — `_net_worth()` transaction sum for credit_card/heloc had no upper date bound; added `Transaction.transaction_date <= date.today()` so future-dated transactions are excluded.
- **Migration 0005 downgrade** — spurious `GRANT USAGE ON TYPE account_type TO hearthledger_app` was included in `downgrade()`; removed.
- **Demo seeds — 403(b) account type** — H1 Priya Nakamura and H2 Carmen Rivera's 403(b) accounts were seeded as `retirement_401k`; corrected to `retirement_403b`.
- **Demo seeds — member date of birth** — All three households were seeded without `date_of_birth` on primary/partner members, causing FIRE `fire_age` to always be null; added realistic DOBs to all six members.
- **Demo seeds — income stream type** — H2 and H3 pension/social_security income streams lacked `is_pre_retirement: False`; added so the projector correctly counts them as post-retirement income (reducing withdrawals, not pre-retirement savings).
- **Demo seeds — idempotency** — `seed_demo_data.py` would crash with an opaque `UniqueViolation` on re-run; replaced with an explicit guard that exits with a readable error if households already exist.
- **Heloc ordering in account type lists** — `AddAccountModal.tsx` and `Accounts.tsx` had `heloc` listed after the `other_liability` catch-all; moved before it so the catch-all remains last.
- **fire.ts API types** — `member_id` was missing from `fireApi.create()` and `fireApi.update()` typed parameter shapes, preventing the frontend from passing attribution through the typed client.

## [0.9.2.0] - 2026-06-20

### Added

- **Phase 7 demo seed script** — `backend/scripts/seed_demo_data.py --household 1|2|3|all` populates HearthLedger with three fictitious households of increasing financial complexity, covering every major feature surface (30 months of transactions, investment snapshots, property valuations, FIRE scenarios, debt records, budgets).
  - **H1 Chen-Nakamura** (Round Rock, TX) — 2 members, 12 accounts, 1 property, ~$899K net worth. Exercises: dual income, Roth IRA contributions, auto loan, IRS refund, seasonal spending.
  - **H2 Okonkwo-Rivera** (Naperville, IL) — 4 members (2 dependents), 19 accounts, 2 properties, ~$3.4M net worth. Exercises: long-term rental, 529 college savings, year-end bonus, access grants, property tax, late rental payment.
  - **H3 Whitfield-Torres** (Brentwood, LA) — 4 members (2 dependents, 1 with elevated grants), 25 accounts, 3 properties, ~$9.5M net worth. Exercises: HELOC, SEP-IRA, STR vacation rental, profit-share lump-sums, partner distributions, equity market dips, property management fees.
- **HELOC account type** — `heloc` added to the `account_type` enum (migration 0005); balance is derived from transaction SUM, consistent with other liability types. Frontend label: "HELOC".
- **FIRE scenario member attribution** — `fire_scenarios.member_id` nullable FK → `household_members` (migration 0005); allows per-member FIRE scenarios alongside household-level scenarios. Exposed in `FireScenarioCreate`, `FireScenarioUpdate`, and `FireScenarioResponse`.

### Fixed

- **AccountType schema** — `"heloc"` was missing from the `AccountType` Pydantic literal in `schemas/account.py`, causing `AccountCreate` to reject valid heloc accounts even after migration 0005 added the DB enum value.
- **FireScenarioService.update() member_id clearing** — `member_id` could not be set back to `None` via PATCH because the update guard used `is not None`; fixed with `model_fields_set` check so an explicit `null` payload clears the field.

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
