# TODOS

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.

---

### Pension PV formula accuracy (post-Phase 8)

**What:** The current pension net worth formula uses a simplified perpetuity:
`monthly_benefit_estimate × 12 / 0.04`. This ignores time-to-retirement (overestimates
for young workers), survivorship benefit rates, and cola_adjustment_rate. Additionally,
updating `monthly_benefit_estimate` retroactively changes ALL historical net worth chart
points since there is no time-series of past estimates.

**Why:** The perpetuity formula gives useful directional signal but is less accurate for
households far from retirement. The retroactive recalculation is a known data model
limitation.

**Pros:** A more accurate PV would use annuity factors with age and expected retirement
date (as in the FIRE projector), making net worth more precise. Historical accuracy
requires a new `PensionEstimateHistory` table.

**Cons:** Significant scope increase. Requires a new DB table, migration, and service
changes. The FIRE projector already has a more accurate model that could be reused.

**Context:** Acknowledged in Phase 8 design doc as a known limitation. The UI label
"~$X estimated PV (4% discount, based on current benefit estimate)" signals the
approximation to the user.

**Depends on:** Phase 8 B2 complete.

---

### Investment positions table (deferred from Wealth Dashboard redesign Phase 4)

**What:** The Investments tab (`/reports/investments`) currently shows only account-level balances for `investment_brokerage` accounts. Add support for: (1) manual entry of individual holdings (ticker, shares, cost basis), (2) a Holdings mix by asset class breakdown, (3) optional brokerage sync for auto-populating positions.

**Why:** The high-fidelity design's "Top positions" table (VTI 42 shares, NVDA 12 shares) and "Holdings mix" donut require per-security data that doesn't exist in the backend yet. HearthLedger is a balance tracker, not a brokerage integration — showing position-level data is a meaningful upgrade to investment insight.

**Pros:** Closes the gap between HearthLedger and tools like Monarch Money for investment tracking. Manual entry works offline with no API keys required. Brokerage sync could auto-update positions if a provider is added.

**Cons:** Requires a new `investment_positions` DB table, migration, CRUD API endpoints, and UI in the Investments tab. Brokerage sync would additionally require an external API integration. Significant scope increase.

**Context:** Explicitly deferred as design decision D2 during the office-hours session (2026-06-19). The Investments tab was intentionally scoped to account-level data for the Phase 4 initial implementation. The TODO comment in `Investments.tsx` marks where this UI would go.

**Depends on:** Wealth Dashboard Phase 4 complete. New `investment_positions` DB schema design (separate planning session needed).

---

### Assets.test.tsx — null-mortgage equity test (Phase 11 deferred)

**Priority:** P2

**What:** Add a Vitest / React Testing Library test to `frontend/src/` that mocks `propertiesApi.getEquity` with `mortgage_balance_visible: false` and verifies the Assets page renders the Sarasota property equity figure without crashing. The Phase 11 design doc (section 2.5, verification checklist) explicitly lists this as a required test before the Phase 11 feature is considered complete.

**Why:** H5 Langford's Sarasota primary home is a cash purchase (`linked_mortgage_account_id = null`). The equity display path for properties without a linked mortgage has not been exercised in the test suite. A crash in this code path would affect any user who creates a real estate account without a linked mortgage.

**Depends on:** ~~Phase 11 H4/H5 seed modules merged~~ — fulfilled by v0.9.4.0. Ready to implement.

---

## Completed

### Context-aware category add buttons on Accounts page (Phase 8 F6)

**Completed:** v0.9.3.0 (2026-06-20) — Per-category "+" buttons on the Accounts page now use context-aware handlers: Banking & Cash opens the add modal filtered to banking types, Liabilities opens it filtered to liability types, and Retirement/Investments/Real estate navigate to their dedicated pages. Previously all "+" buttons opened the same modal, which showed no options for Retirement/Investment/Real estate categories.

### WeasyPrint macOS test skip

**Completed:** v0.9.2.0 (2026-06-20) — `test_phase_5.py` uses `ctypes.util.find_library("gobject-2.0")` to auto-detect library availability and marks PDF tests with `pytest.mark.skipif` when the library is absent. No manual platform flag needed.

### Fix RealEstateService.update() nullable pattern

**Completed:** v0.7.0.0 (2026-06-18) — `real_estate.py:update()` now uses `model_fields_set` iteration; `linked_mortgage_account_id` can be cleared to null.

### Extract snapshot query to AccountRepository

**Completed:** v0.7.0.0 (2026-06-18) — `AccountRepository.latest_snapshot(account_id)` returns `(balance, date)` tuple used by both equity endpoint and report service.
