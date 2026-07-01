# Rules-Based Categorization (R4) — Implementation Progress

Branch: `feat/rules-categorization`
Part of the ingest arc (R4 of the design doc `jason-main-design-20260630-154717.md`). Depends on the R1-R3 foundation (shipped v0.23.22.0).

Deterministic payee → category rules: the memory layer behind "HearthLedger remembers this payee." Runs on import-promote and manual entry. LLM categorization (R5b) only ever handles the tail these rules miss.

## Locked decisions

- **Apply scope:** fill-empty only (never override a category a human or prior rule set) + an on-demand backfill action for existing uncategorized transactions.
- **Match types:** `exact` / `contains` / `regex`, priority-ordered (higher wins, older breaks ties). Created via CRUD + a "suggest from history" endpoint that mines payee → dominant category and proposes `contains` rules the user confirms (nothing auto-created).

## What landed

| Piece                                                     | Status |
| --------------------------------------------------------- | ------ |
| category_rule model + migration 0024                      | ✅     |
| CategorizationService (match / CRUD / suggest / backfill) | ✅     |
| Wired into promote + manual create (fill-empty)           | ✅     |
| API + schemas + router                                    | ✅     |
| Tests + this doc                                          | ✅     |

### Details

- `db/models/category_rule.py` + migration `0024` (household_id-indexed, `ck_category_rules_match_type` CHECK on exact/contains/regex). Registered in `models/__init__.py`.
- `services/categorization.py`:
  - `match(household_id, payee)` — highest-priority active rule whose pattern matches; `_rule_matches` is case-insensitive for exact/contains (normalized), regex searched case-insensitively against the raw payee. Invalid regex never matches (and is rejected at create time), so a bad row can't raise mid-categorization.
  - CRUD (`create`/`update` `@audit`-decorated, `delete` audited manually), category-ownership + regex validation.
  - `suggest_from_history` — mines reviewed categorized transactions (coalescing payee_normalized/payee_raw) into `contains` candidates for payees recurring ≥3× with a dominant category, skipping payees an active rule already covers.
  - `backfill_uncategorized` — applies active rules to existing uncategorized transactions (fill-empty), one audit row per newly-categorized transaction.
- Wiring: `PromoteService` fills `category_id` from a rule when a staged row has none (matches on `payee_raw`); `TransactionService.create` fills from a rule when the caller supplies no category (matches on `payee_normalized`). Both are fill-empty — an explicit category is never overridden.
- `api/v1/category_rules.py`: `GET/POST/PATCH/DELETE /category-rules`, `GET /category-rules/suggestions`, `POST /category-rules/backfill`. Registered in the router.
- Tests: `tests/unit/test_categorization_matching.py` (7 ✓ — exact/contains/regex/case/invalid-regex/priority-normalize), `tests/integration/test_category_rules.py` (7 ✓ — CRUD, invalid-regex 400, fill-on-manual-create, **never-override explicit category**, apply-on-promote, priority ordering, suggest-from-history + backfill). Regression: promote/staging/e2e/phase-2/txn-service suites (44 ✓).

## Not in scope (still deferred)

- Frontend UI for managing rules + reviewing suggestions (backend-only here, like the rest of the ingest arc).
- LLM categorization for the unmatched tail (R5b, gated on the Ollama spike).
- Applying rules retroactively to already-_categorized_ transactions (deliberately never — fill-empty only).
