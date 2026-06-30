# Ingest API Foundation — Implementation Progress

Branch: `feat/ingest-api-foundation`
Design doc: `~/.gstack/projects/jdmacleod-financial-dashboard/jason-main-design-20260630-154717.md`
Scope: R1-R3 foundation (PAT auth, staging endpoint + worker, ingest CLI). R4/R5/R6 deferred.

Tracks the 8 build tasks (T1-T8) from the eng review. Each task: status, what landed, files, how verified.

| Task | Title                                                                          | Status         |
| ---- | ------------------------------------------------------------------------------ | -------------- |
| T1   | PAT model & SHA-256+prefix verification                                        | ✅ done        |
| T2   | Shared ctx resolver + prefix routing                                           | ✅ done        |
| T3   | staging_transaction table + sync endpoint + server PII                         | ✅ done        |
| T4   | Shared dedupe/transfer service (batch-prefetch, per-row failure, unique index) | ✅ done        |
| T5   | Audited promote-on-review (fold deferred to frontend, see TODOS)               | ✅ done        |
| T6   | Migrations: source enum→VARCHAR + confidence                                   | ✅ done        |
| T7   | Ingest CLI package                                                             | ✅ done        |
| T8   | E2E tests (round-trip; PAT lifecycle)                                          | 🟡 in progress |

Legend: ⬜ pending · 🟡 in progress · ✅ done · ⚠️ done-with-concerns

---

## Locked decisions (from eng review)

- PAT token format `hl_pat_<prefix>.<secret>`; store SHA-256(secret) + indexed prefix; constant-time compare. NOT bcrypt.
- Primary-only minting; columns prefix/token_hash/label/capability/created_by/expires_at/last_used_at/revoked_at; live revocation (re-check every request, never cache ctx); single `import-write` capability in v1.
- PAT lifecycle audited as auth events via `write_auth_event` (consistent with auth.py; avoids the @audit tuple-return problem; token_hash never logged).
- Bearer dependency routes by `hl_pat_` prefix → PAT path, else JWT. Both resolve the SAME VisibilityContext via one shared DB-backed resolver (household+member+role, is_active check). JWT path DB-derives role.
- Staging rows in a SEPARATE `staging_transaction` table → balances can't see them until promote. Synchronous staging (no ARQ). Server re-runs PII classification + encryption (authority). DB unique index `(account_id, external_id) WHERE external_id IS NOT NULL` for idempotency. Per-row failure capture. Promote = one audit row per entity.
- `transactions.source` PG enum → VARCHAR+CHECK (reversible); add `transactions.confidence NUMERIC(4,3) NULL`.

---

## T1 — PAT model & verification

Status: ✅ done

- `core/security.py`: `generate_pat` / `parse_pat` / `verify_pat_secret` (`hl_pat_<prefix>.<secret>`, SHA-256, constant-time compare).
- `db/models/personal_access_token.py` + migration `0021` (unique-indexed prefix). Registered in `models/__init__.py`.
- `services/pat.py`: `PATService.create` (primary-only, active-token cap), `list`, `revoke`, `authenticate` (live revoke/expiry, updates last_used_at). Lifecycle audited via `write_auth_event`.
- `api/v1/pat.py`: POST/GET/DELETE `/personal-access-tokens` (session-only via `require_session_ctx`). Registered in router.
- `core/audit.py`: `token_hash` added to `AUDIT_SECRET_FIELDS`.
- `core/config.py`: `pat_default_ttl_days=90`, `pat_max_active=10`.
- Tests: `tests/unit/test_pat_security.py` (8 ✓), PAT lifecycle in `tests/integration/test_pat.py`.

## T2 — Shared ctx resolver + prefix routing

Status: ✅ done

- `core/visibility.py`: `_resolve_identity` (DB-derives household+member+role, is*active on user AND member). `get_visibility_ctx` routes by `hl_pat*` prefix → PAT path, else JWT — both via the shared resolver. **JWT path now DB-derives role** (closes stale-role gap).
- `VisibilityContext` gained `auth_method` + `capability`. `require_session_ctx` (rejects PAT — no escalation) and `require_import_write_ctx` (session writer OR import-write PAT) added.
- `core/throttle.py`: best-effort in-process per-IP failure throttle for bad PATs (documented limitation; Redis follow-up).
- Tests: `tests/integration/test_pat.py` (9 ✓) — PAT auth on a general endpoint, session-only management, revoke-then-fail, owner-deactivated, **JWT role DB-derived regression**. Existing auth/accounts/members/smoke suites (34 ✓) confirm no regression on the 138 JWT handlers.

## T3 — Staging table + sync endpoint + server PII

Status: ✅ done

- `db/models/staging_transaction.py` + migration `0022` (separate table; indexes on account_id, batch_id; partial unique index `(account_id, external_id) WHERE external_id IS NOT NULL`). Registered in `models/__init__.py`.
- `core/pii.py`: deterministic `redact_pii` (mask account/card/routing digit-runs to last 4) + `contains_pii` (Luhn-aware). **Server is the trust boundary** — re-redacts regardless of what the CLI sent.
- `services/dedupe.py`: batch-prefetched `DedupeIndex` over committed + staged rows in the batch's date window (kills the per-row N+1); `is_duplicate` (external_id or date+amount+fuzzy payee) + `remember` (intra-batch dups).
- `services/staging.py`: `StagingService.stage` — synchronous (no ARQ), per-row savepoint (one bad row can't poison the batch), redacts PII, dedupes, IntegrityError = idempotency backstop. Returns batch_id + staged/skipped/failed counts. `list_batch` for the review queue.
- `schemas/staging.py`: `StagingRow` / `ImportStagingRequest` (client batch_id, ≤5000 rows) / `ImportStagingResponse` / `StagingTransactionResponse`.
- `api/v1/imports.py`: `POST /accounts/{id}/import/staging` (`require_import_write_ctx` = session writer OR import-write PAT) + `GET .../staging/{batch_id}`.
- Tests: `tests/unit/test_pii.py` (7 ✓), `tests/integration/test_staging.py` (7 ✓) — **balances exclude staging regression**, idempotent re-batch, intra-batch dup, server PII redaction, partner-session + PAT auth, 404.

## T6 — Migrations: source enum→VARCHAR + confidence

Status: ✅ done

- `db/models/transaction.py`: `source` is now `String(16)` (was PG enum); `TRANSACTION_SOURCES` gains `json`/`pdf`/`ingest`; new `confidence: Numeric(4,3) | None` column.
- Migration `0023`: drops the column default, converts `source` enum→VARCHAR, drops the `transaction_source` type, re-adds the default, adds a `ck_transactions_source` CHECK, adds `confidence`. Reversible `downgrade()` reclassifies new sources→`manual` before recreating the enum.
- Validated: existing transaction CRUD + staging suites pass against the migrated schema.

## T4 — Shared dedupe/transfer service

Status: ✅ done

- `services/dedupe.py` `DedupeIndex` (built in T3) now also backs `run_import_job`: removed the per-row `_is_duplicate` (the N+1), prefetch once, dedupe in memory, `remember` for intra-batch. Behavior-preserving.
- The 4 `_is_duplicate` unit tests migrated to exercise `build_dedupe_index`/`DedupeIndex` directly. Worker transfer-pairing helpers unchanged. Existing import suites (21 ✓) green.

## T5 — Audited promote-on-review

Status: 🟡 partial

- ✅ `services/promote.py` `PromoteService.promote_batch`: staging rows → `transactions` (one audit row PER promoted entity; the @audit decorator can't batch), source + confidence carried, staging rows deleted. Post-promote transfer pairing across the household, each mutation audited (the old worker mutated committed rows silently).
- ✅ `POST /accounts/{id}/import/staging/{batch_id}/promote` (`require_import_write_ctx`).
- ✅ Tests `tests/integration/test_promote.py` (4 ✓): round-trip (balance reflects only after promote), staging cleared, one-audit-row-per-txn, cross-account transfer pairing + audit, 404.
- ⏭️ **Fold of the SPA file-upload path onto staging/promote: DEFERRED** (user decision 2026-06-30). It changes the upload UX and needs a frontend review/promote queue (outside R1-R3 backend scope). Captured in `TODOS.md`. The promote backend + endpoint are ready for it.

## T7 — Ingest CLI package

Status: ✅ done

- New standalone package `ingest/` (`hearthledger_ingest`) with its own `pyproject.toml` + `hearthledger-ingest` console script. Privacy-first sidecar: parses locally, pushes only plaintext fields, server re-redacts.
- `parsers.py`: deterministic `parse_csv` (auto header mapping, currency/paren-negative handling) + `parse_json` → canonical rows (confidence 1.0). `pii.py`: local redaction hint (mirrors server). `client.py`: `IngestClient.stage` (token bearer, client batch_id for idempotency, injectable httpx client). `cli.py`: argparse entry (`--account-id`, `--api-url`, `--token`/`HEARTHLEDGER_TOKEN`, `--dry-run`).
- Tests: `ingest/tests/` (12 ✓) — parser mapping/currency/PII/JSON/dispatch, client posts to staging with token (MockTransport), CLI dry-run + token-required + bad-file.
