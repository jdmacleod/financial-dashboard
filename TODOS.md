# TODOS

### DESIGN.md — HearthLedger design system document

**What:** Run `/design-consultation` to produce a `DESIGN.md` at the repo root documenting HearthLedger-specific design tokens: type scale (Archivo headings, Spectral body), color palette (indigo-600 accent, gray-200 borders), component vocabulary (section header pattern, range toggle pill style, modal pattern), and spacing rules.

**Why:** Without a design system document, each new UI feature is reviewed against universal principles instead of HearthLedger-specific conventions. The `plan-design-review` skill flagged its absence during the Budgets sort/filter design review. Without it, decisions like "what should the sort select look like?" get made ad-hoc instead of from a documented token.

**Pros:** Future UI reviews become faster and more precise. New contributors have a reference. Prevents design drift as the feature set grows.

**Cons:** Takes one session. Requires keeping the document current as the design evolves.

**Depends on:** Nothing.

---

### Sort/filter state persistence — Budgets tab (Deferred from v0.17.0.0)

**What:** After the Budgets tab sort/filter controls ship, optionally persist the user's chosen sort keys (for Budget vs Actuals and All Budgets) to `localStorage`. Currently session-only React state that resets on navigation.

**Why:** A household that always reviews budgets in "Name A-Z" order has to re-apply the sort every visit. A power user with 20+ categories finds alphabetical scanning essential and would benefit from the preference being remembered. Raised during the sort/filter design review.

**Pros:** ~15 lines of `useEffect` code. No schema or backend changes. Purely additive.

**Cons:** localStorage has no cross-device sync. If the sort option keys ever change, stored values become stale (would need versioning or fallback). Adds a `useEffect` dependency to the component.

**Context:** Session-only state was the v0.17.0.0 choice because it covers the common case with zero overhead. Persistence is a progressive enhancement for power users.

**Depends on:** Budgets sort/filter feature shipped (v0.17.0.0).

---

### Quarterly budget period — Budgets tab (Deferred from v0.16.0.0)

**What:** Add `"quarterly"` as a valid budget period alongside `"monthly"` and `"annual"`. The Budgets tab would show a `÷3` monthly proration badge and the backend would divide by 3 in the budget-vs-actuals report.

**Why:** The original devex review request mentioned "quarterly or yearly items." Only annual was implemented because it covers the most common case (annual subscriptions, insurance, property tax).

**Cons:** Adds a third enum value that must be threaded through schema, service, DB migration, and UI radio buttons. Modest scope but requires an Alembic migration to update the `budgetperiod` Postgres enum.

**Depends on:** v0.16.0.0 shipped.

---

### Unique constraint on (household_id, category_id, effective_from) in budgets table

**What:** Add a DB-level unique constraint to prevent two budgets for the same category and start date. Currently prevented only by application logic; a race condition could create duplicates.

**Why:** Adversarial review (v0.16.0.0) identified that `list_active_for_period` returns all matching budgets and the service discards duplicates with last-wins dict behavior. A uniqueness constraint enforces the intent at the DB layer.

**Cons:** Requires an Alembic migration. May need a data cleanup pass if any households have existing duplicates.

**Depends on:** v0.16.0.0 shipped.

---

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.

---

### Investment positions — optional brokerage sync (residual)

**What:** Auto-populate positions from an external brokerage provider. The manual
positions feature — per-ticker rollup ("Top positions") and "Holdings mix by asset class"
donut — is implemented (see Completed below). Only the optional brokerage-sync leg of the
original item remains.

**Why:** HearthLedger is a balance tracker with no external connections by design; a sync
provider would require an API integration and credential handling, mirroring the real
estate valuation provider pattern.

**Cons:** External API integration, credentials, and a scheduled sync task. Significant
scope; out of scope for v1's no-connections stance.

**Context:** Positions rollup built over the existing `investment_lot` (cost-basis) data
with a new `asset_class` column (migration 0009), a `GET /investment-positions` endpoint,
and an `InvestmentPositionsPanel` on the Investments page.

**Depends on:** Positions rollup (done).

---

### Member retirement target age (Identity layer — deferred from v0.21.0.0)

**What:** Add a `member.retirement_target_age` column (nullable smallint) plus a small UI to set it. Drives when FIRE switches from accumulation to withdrawal and anchors the milestone timeline.

**Why:** Approach C (the financial-identity layer) called for it, but it shipped without a consumer, so the column was descoped to avoid dead schema. It becomes load-bearing once the milestone timeline (below) or a FIRE enhancement reads it.

**Cons:** Additive migration + a form field; low risk. Only worth doing alongside a consumer.

**Depends on:** Nothing hard; pairs with the milestone timeline.

---

### Account tax-treatment override UI (Identity layer — deferred from v0.21.0.0)

**What:** A select in the account create/edit form to set `tax_treatment` (pretax / roth / taxable), overriding the account-type-based seed from migration 0014.

**Why:** RMD eligibility keys off `tax_treatment`. The column is seeded automatically, but accounts whose treatment isn't implied by type (a generic "IRA", after-tax 401k balances, a rollover) can't be corrected today, so their RMD may be wrong.

**Cons:** Small frontend form change plus exposing the field on the account schema/API.

**Depends on:** `account.tax_treatment` (shipped v0.21.0.0).

---

### Self-service profile page + self-or-primary DOB authz (Identity layer — deferred from v0.21.0.0)

**What:** A "Your profile" page under the user dropdown, and a self-or-primary authorization rule so a member can edit their own date of birth (primary can edit anyone; role changes stay primary-only).

**Why:** This is the one place the implementation diverged from an approved CEO-review decision (Decision 3: self-or-primary). DOB editing currently lives in the Members admin drawer and is primary-only, so a partner can't fix their own birthdate without the primary.

**Cons:** New page + a self-or-primary check in `MemberService.update`; small but security-relevant (it widens who can mutate a member).

**Depends on:** DOB editing UI (shipped v0.21.0.0).

---

### Wire RMD into FIRE projections (Identity layer T9 — in progress)

**What:** Feed each member's computed required minimum distribution into the FIRE projection as post-retirement supplemental income, so projections reflect forced withdrawals.

**Why:** FIRE already consumes member DOB and the RMD engine exists; connecting them makes long-horizon projections account for the cash RMDs actually produce.

**Cons:** Couples `fire_service` to `RmdService`; needs care so a member with no pretax balance or no DOB is a clean no-op.

**Depends on:** RMD engine (shipped v0.21.0.0). Being implemented now.

---

### Age-milestone timeline UI (Identity layer T10 — deferred from v0.21.0.0)

**What:** A forward-looking timeline (Profile or Retirement page) rendering each member's upcoming age-triggered events: 59½ early withdrawals, 62 Social Security earliest, 65 Medicare, full retirement age, and RMD start. Needs a `milestones()` helper plus an FRA-by-birth-year table in `app/services/age.py` (only `rmd_start_age` exists today).

**Why:** The "felt payoff" of the identity layer — entering a birthday surfaces "RMDs begin 2041, Medicare 2033" instead of an inert number. Empty/partial states (no DOB) are load-bearing.

**Cons:** New `age.py` helpers (FRA table is a graduated lookup), a new UI surface, and design polish (run `/plan-design-review` first).

**Depends on:** `age.py` (shipped v0.21.0.0); pairs with retirement target age.

---

### Batch prior-year snapshot reads in the RMD engine (Identity layer E4 — deferred from v0.21.0.0)

**What:** `rmd._prior_year_end_pretax_balance` issues one query per pretax account (an N+1). Batch the prior-year snapshot reads into a single keyed query, mirroring `report.py`'s batched-balance pattern.

**Why:** Eng-review flagged it. Harmless at household scale, but it's the documented N+1 and the report service already has the batched pattern to copy.

**Cons:** Minor refactor; needs a test that the batched result matches the per-account loop.

**Depends on:** RMD engine (shipped v0.21.0.0).

---

### Structured logging in the RMD engine (Identity layer T12 — deferred from v0.21.0.0)

**What:** Add an info-level log line in `RmdService.required_distributions` (member, attained age, pretax base, snapshot date, computed RMD) so a "why is my RMD $0" report is reconstructable from logs.

**Why:** Observability was specced but not built; the engine has several silent empty/partial branches.

**Cons:** Trivial; a few log statements.

**Depends on:** RMD engine (shipped v0.21.0.0).

---

### Social Security claiming-age modeling (Identity layer — deferred scope)

**What:** Per-member Social Security claiming age with benefit adjustment (reduction before FRA, delayed-retirement credits to 70) and FRA lookup by birth year; feed the result into FIRE supplemental income.

**Why:** Claiming age is one of the biggest retirement levers. A self-contained engine the financial-identity layer was designed to host.

**Cons:** Benefit-adjustment math + FRA table; its own PR. Med risk (correctness).

**Depends on:** `age.py` FRA table (shared with the milestone timeline).

---

### Filing status attribute (Identity layer — deferred scope)

**What:** Store household/member filing status (single / MFJ / HoH).

**Why:** Cheap to store, but only pays off once a tax-estimate engine consumes it (brackets, standard deduction, SS provisional-income taxation).

**Cons:** Mild YAGNI until the tax engine is scheduled; best shipped with its consumer.

**Depends on:** Tax-estimate engine (below).

---

### State of residence attribute (Identity layer — deferred scope)

**What:** Store the household's state of residence for future state-tax modeling.

**Why:** Needed for any state-level tax estimate; HearthLedger is federal/USD-focused today.

**Cons:** Placeholder until state-tax logic exists; not scheduled.

**Depends on:** State-tax modeling (not scheduled).

---

### Roth-conversion modeling (Identity layer — deferred scope)

**What:** Project converting pretax balances to Roth in low-income years to shrink future RMDs, showing the RMD/tax tradeoff over time.

**Why:** High-value for FIRE households once `tax_treatment` (shipped) and a tax estimate exist.

**Cons:** Substantial (L); depends on a tax estimate. Med risk.

**Depends on:** `account.tax_treatment` (shipped v0.21.0.0) + tax-estimate engine.

---

### Federal/state tax-estimate engine (Identity layer — deferred scope)

**What:** Estimate federal (and optionally state) tax: brackets, standard deduction, Social Security provisional-income taxation, applied to RMD/SS/withdrawal figures so they can be shown after-tax.

**Why:** Turns gross retirement numbers into spendable ones and unblocks filing status, state, and Roth-conversion modeling.

**Cons:** XL, with ongoing annual table maintenance and real correctness risk. Its own multi-PR program.

**Depends on:** Filing status + state of residence attributes.

---

## Completed

### Include SBLOC/margin in transaction-tracked liability valuation

**Completed:** v0.20.1.0 (2026-06-24) — Added `sbloc` and `margin` to
`TXN_TRACKED_LIABILITY_TYPES` in `app/services/report.py`, so revolving credit
lines value from their running transaction sum and a Debt record can no longer
pin them to a static balance (the v0.19.0.0 flat-line bug). Preserved the
snapshot fallback by extending the transaction-tracked branch to txn → Debt →
snapshot → 0, which also gives credit cards / lines of credit / loans a snapshot
fallback they lacked. Behavior-neutral for the sample data (verified by the
per-household net-worth agreement test). Two regression tests added.

### Investment positions rollup — Top positions + Holdings mix

**Completed:** v0.15.0.0 (2026-06-22) — Cost-basis lots
now roll up into a per-ticker "Top positions" table and an asset-class "Holdings mix"
donut on the Investments page. Added `investment_lot.asset_class` (migration 0009), a
`GET /investment-positions` endpoint (`InvestmentLotService.positions_summary`), and
typed frontend panel. Seed lots are auto-classified by ticker for a meaningful demo mix.
Cost basis is used (no live prices). Optional brokerage sync remains deferred (above).

### Pension PV formula rework + historical estimate time-series

**Completed:** v0.15.0.0 (2026-06-22) — Replaced the
perpetuity (`annual / 0.04`) with a model that discounts deferred benefits over the years
to eligibility, models COLA growth as a growing annuity, values a finite life annuity, and
adds the survivor benefit. Centralized in `app/services/pension_valuation.py`; the report
layer and the net-worth UI now use the shared value (`PensionAnnotation.estimated_pv`).

Added `PensionEstimateHistory` (migration 0010): `PensionService` records an estimate
snapshot on create and whenever a PV-relevant field changes, and each net-worth point is
valued from the estimate in effect at that date (`pension_value_at` / `effective_estimate`).
Editing today's benefit estimate no longer rewrites historical chart points. Pensions
predating the table fall back to current fields; existing rows were backfilled in the
migration. This fully closes the original Phase 8 item.

### Retirement income breakdown in cash-flow report

**Completed:** v0.15.0.0 (2026-06-22) — The cash-flow
report now breaks retirement income into labeled buckets (Social Security / Pension /
RMDs) via `CashFlowReport.retirement_income`; the Cash flow page shows a panel that hides
itself when the household draws no retirement income. (Phase 11 CEO plan, Phase 12
candidate.)

### Assets.test.tsx — null-mortgage equity test

**Completed:** v0.15.0.0 (2026-06-22) — Added a Vitest
case covering a cash-purchased property (`linked_mortgage_account_id: null`,
`mortgage_balance_visible: false`): asserts the equity figure renders and no mortgage line
appears. Closes the Phase 11 §2.5 verification item.

### Context-aware category add buttons on Accounts page (Phase 8 F6)

**Completed:** v0.9.3.0 (2026-06-20) — Per-category "+" buttons on the Accounts page now use context-aware handlers: Banking & Cash opens the add modal filtered to banking types, Liabilities opens it filtered to liability types, and Retirement/Investments/Real estate navigate to their dedicated pages. Previously all "+" buttons opened the same modal, which showed no options for Retirement/Investment/Real estate categories.

### WeasyPrint macOS test skip

**Completed:** v0.9.2.0 (2026-06-20) — `test_phase_5.py` uses `ctypes.util.find_library("gobject-2.0")` to auto-detect library availability and marks PDF tests with `pytest.mark.skipif` when the library is absent. No manual platform flag needed.

### Fix RealEstateService.update() nullable pattern

**Completed:** v0.7.0.0 (2026-06-18) — `real_estate.py:update()` now uses `model_fields_set` iteration; `linked_mortgage_account_id` can be cleared to null.

### Extract snapshot query to AccountRepository

**Completed:** v0.7.0.0 (2026-06-18) — `AccountRepository.latest_snapshot(account_id)` returns `(balance, date)` tuple used by both equity endpoint and report service.
