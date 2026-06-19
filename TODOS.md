# TODOS

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.

---

## Completed

### Fix RealEstateService.update() nullable pattern

**Completed:** v0.7.0.0 (2026-06-18) — `real_estate.py:update()` now uses `model_fields_set` iteration; `linked_mortgage_account_id` can be cleared to null.

### Extract snapshot query to AccountRepository

**Completed:** v0.7.0.0 (2026-06-18) — `AccountRepository.latest_snapshot(account_id)` returns `(balance, date)` tuple used by both equity endpoint and report service.
