# TODOS

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.

---

---

### AddAccountModal type filtering on Assets page (deferred from Phase 8 F6)

**What:** After F3 narrows the Accounts list to transaction-based types, users can still
add real estate, pension, or investment accounts via the AddAccountModal on the Accounts
page. After creation, those accounts won't appear in the Accounts list — they'll be in
Assets. A user who doesn't know to check Assets may think their account wasn't created.

**Why:** The UX creates a silent "where did my account go?" moment. The fix requires
either (a) extracting AddAccountModal into a shared component with an `allowedAssetTypes`
prop so each page can control the type list, or (b) adding a post-creation banner/redirect
that guides the user to Assets.

**Pros:** Eliminates a confusing UX gap. Makes the Accounts/Assets mental model consistent.

**Cons:** Requires extracting AddAccountModal into a shared component (a clean but
non-trivial refactor) OR adding post-creation navigation logic.

**Context:** Explicitly deferred in Phase 8 design doc (F6 decision). Current behavior:
AddAccountModal uses the full ASSET_TYPES list, but the Accounts page list filter uses
the narrowed DISPLAY_ASSET_TYPES. Both are defined inside Accounts.tsx.

**Depends on:** Phase 8 F2+F3 complete.

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

## Completed

### Fix RealEstateService.update() nullable pattern

**Completed:** v0.7.0.0 (2026-06-18) — `real_estate.py:update()` now uses `model_fields_set` iteration; `linked_mortgage_account_id` can be cleared to null.

### Extract snapshot query to AccountRepository

**Completed:** v0.7.0.0 (2026-06-18) — `AccountRepository.latest_snapshot(account_id)` returns `(balance, date)` tuple used by both equity endpoint and report service.
