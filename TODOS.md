# TODOS

## Phase 7 — Real Estate & Pension Enhancement

### Fix RealEstateService.update() nullable pattern (Phase 7 PR)

**What:** Change `real_estate.py:update()` to use `model_fields_set` for nullable fields
(specifically `linked_mortgage_account_id`).

**Why:** The current `if data.field is not None` pattern prevents clients from ever clearing
`linked_mortgage_account_id` to null (unlinking a mortgage from a property). A user who linked
the wrong mortgage account has no way to fix it without a direct DB edit.

**Pros:** Consistent with `transaction.py:128` pattern; fixes real user workflow.

**Cons:** Minimal — 3-line change, low risk.

**Context:** Found during Phase 7 eng review while specifying the same fix for PensionService.
Start by reading `backend/app/services/real_estate.py:109-135` and applying the `model_fields_set`
iteration pattern from `transaction.py:128`.

**Depends on:** None.

---

### Extract snapshot query to AccountRepository (Phase 7 PR)

**What:** Add `AccountRepository.latest_snapshot(account_id: UUID) -> tuple[Decimal, date] | None`
that returns `(balance, snapshot_date)` for the most recent `AccountSnapshot`.

**Why:** `ReportService._snapshot_balance_at()` and the new equity endpoint both query
`ORDER BY snapshot_date DESC LIMIT 1` independently. Two implementations will drift.

**Pros:** Single source of truth for snapshot lookup; 3-line extraction.

**Cons:** Adds a method to an already-large repository. Marginal DRY at this scale.

**Context:** Found during Phase 7 eng review. `ReportService._snapshot_balance_at()` (returns
balance only) and the equity endpoint (needs balance + date) are similar enough that a
`(balance, date)` tuple return handles both. The equity endpoint can call
`account_repo.latest_snapshot(account_id)` rather than duplicating the query inline.

**Depends on:** None.

---

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.
