# TODOS

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

## Completed

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
