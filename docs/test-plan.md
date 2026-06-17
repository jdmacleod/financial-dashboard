# Test Plan — reaching ≥90% coverage

This is a concrete, prioritized test list, not test code. It exists because the
repo currently has **zero test files** (no `tests/`, `conftest.py`, pytest
config, `*.test.*`, or `__tests__/` anywhere) and **no test infrastructure
wired up at all** — see "Infra gaps" below, which block any coverage number
from meaning anything even once tests exist.

---

## 0. Infra gaps to close first

Without these, a 90% number is unenforceable and will regress silently.

1. **No CI test job.** `.github/workflows/ci.yml` runs ruff/mypy (backend) and
   eslint/tsc/build (frontend) — no `pytest` step, no `vitest` step anywhere.
2. **No coverage threshold.** `backend/pyproject.toml` has `pytest-cov` as a
   dev dependency but no `[tool.coverage.report] fail_under = 90` (or
   equivalent `--cov-fail-under=90` CI flag).
3. **No frontend test runner installed.** `frontend/package.json` has zero
   `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, or
   `jsdom` in `devDependencies`, and no `test`/`coverage` script.
4. **No test DB fixture strategy documented.** Integration tests need a
   throwaway Postgres database with the baseline migration applied and the
   `hearthledger_app` role's restricted `audit_log` grants in place — the
   restricted-grants behavior (CLAUDE.md rule #3) can only be verified
   against a real Postgres instance, not SQLite or a mocked session.

**Action items:**

- Add `[tool.coverage.run] source = ["app"]` and `[tool.coverage.report] fail_under = 90` to `backend/pyproject.toml`; add a `pytest --cov` CI step.
- `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom @vitest/coverage-v8`; add `"test": "vitest run --coverage"` script; add `coverage.thresholds.lines = 90` to `vite.config.ts`; add a CI step.
- Stand up a `docker-compose`-based test Postgres in CI (or reuse the dev one) and a `conftest.py` fixture that creates a fresh schema per test session via Alembic, then truncates between tests.

---

## 1. Backend — unit tests (no DB required, or DB mocked)

| Module                    | What to test                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Why it matters                                                                                                    |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `core/security.py`        | `hash_password`/`verify_password` roundtrip; wrong password rejected; `create_access_token`/`create_refresh_token`/`create_reauth_token` payload fields + expiry deltas; `decode_token` rejects wrong `type`, rejects expired token, rejects tampered signature                                                                                                                                                                                                                                                                                                                                                               | JWT/bcrypt is the entire trust boundary                                                                           |
| `core/encryption.py`      | `encrypt`/`decrypt` roundtrip for ASCII + unicode; nonce differs across calls on identical plaintext; `decrypt` raises on tampered ciphertext (AEAD tag check); empty string roundtrip                                                                                                                                                                                                                                                                                                                                                                                                                                        | This is the only thing standing between PII and plaintext storage (rule #6)                                       |
| `core/visibility.py`      | `VisibilityContext.is_primary`/`can_export_executor`/`can_write` across all 3 roles (9 cases — explicitly required by CLAUDE.md's testing section); `get_visibility_ctx`: valid token happy path, missing/garbled token → 401, no household found → 403, missing `role` claim defaults to `"partner"`                                                                                                                                                                                                                                                                                                                         | RBAC correctness is the core security model                                                                       |
| `core/audit.py`           | `_snapshot` excludes `AUDIT_EXCLUDED_FIELDS` keys entirely (not just nulls them) for both encrypted-PII and auth-secret fields; `_diff` only returns changed keys; `@audit` decorator writes exactly one row on success, writes **zero** rows if the wrapped function raises before returning, and never includes a key from `AUDIT_EXCLUDED_FIELDS` in `previous_value`/`new_value` even when the row's `_prev_snapshot` was captured pre-mutation (this exact bug — capturing `_prev_snapshot` without the exclude set — was found and fixed in `account.py`/`member.py` during this review; regression-test it explicitly) | Append-only audit log + rules #2/#4 are non-negotiable                                                            |
| `repositories/account.py` | `get_visible(ctx)` returns only accounts the role/grant combination permits: primary sees all household accounts; partner sees only accounts they own or have an active `AccountAccessGrant` for; dependent sees only their own; revoked/inactive grants are excluded; `get_by_id` raises 404 for an existing-but-invisible account (must not leak existence)                                                                                                                                                                                                                                                                 | CLAUDE.md rule #1 — this is the explicitly-named permission matrix the project's own testing section calls out    |
| `services/user.py`        | `create` rejects duplicate email (409); non-primary caller of `create`/`update(is_active=...)`/`deactivate` gets 403; a user can update their own `email` but not their own `is_active`; `deactivate` clears `refresh_token_hash`                                                                                                                                                                                                                                                                                                                                                                                             | Just-fixed audit gap + permission boundary                                                                        |
| `services/account.py`     | `create`/`update`/`deactivate` each produce exactly one `audit_log` row whose `previous_value`/`new_value` never contain `institution_name_enc`/`account_number_enc`/`routing_number_enc`/`notes_enc` even when those fields are non-null and unchanged by the update (the leak this review fixed); non-owner partner cannot update another member's solely-owned account; access grant create/revoke reject non-owner grantee, reject self-grant to the account owner                                                                                                                                                        | Rule #4 regression coverage + grant logic                                                                         |
| `services/member.py`      | Last-primary protection: cannot deactivate or demote the sole remaining `primary` member; non-primary caller gets 403 on create/update/deactivate                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Household lockout prevention                                                                                      |
| `services/setup.py`       | `run()` rejects a second call once a household exists (409); first call writes exactly one `household.setup_completed` audit row (the gap fixed in this review); system categories are copied from the `SYSTEM_HOUSEHOLD_ID` template into the new household                                                                                                                                                                                                                                                                                                                                                                  | Bootstrap correctness — only runs once per install                                                                |
| `services/auth.py`        | Login success path returns valid access+refresh tokens and writes an `auth` audit event; wrong password increments `failed_login_attempts` and writes a failure event; `MAX_LOGIN_ATTEMPTS`-th failure sets `locked_until` and further attempts are rejected even with the correct password until `LOCKOUT_MINUTES` elapses; `refresh` rejects an access-type token; `reauth` token is rejected if reused (single-use semantics, once Phase 5 wires the Redis check)                                                                                                                                                          | Brute-force hardening (`MAX_LOGIN_ATTEMPTS`/`LOCKOUT_MINUTES` env vars exist — confirm they're actually enforced) |

## 2. Backend — integration tests (`httpx.AsyncClient` + real test DB)

- `POST /api/v1/setup` happy path, then a second call returns 409.
- Auth: login, refresh, logout, reauth, lockout-after-N-attempts, end-to-end through the API (not just the service layer).
- Members: full CRUD with 403 enforcement for non-primary roles.
- Accounts: full CRUD + access-grant create/revoke with 403 enforcement; **visibility enforcement through the actual API response**, not just the repository (a partner's `GET /accounts` must not list a primary-only account even if the repository layer is correct — route-level filtering bugs are a different failure mode).
- Users: create/update/deactivate with the just-fixed `@audit` coverage — assert an `audit_log` row exists after each call and that it excludes `hashed_password`.
- `GET /api/v1/audit-log` (once Phase 3 ships): 403 for partner/dependent roles (explicitly an acceptance criterion in `phase-3-analysis.md`).
- DB-permission test: using the `hearthledger_app` role directly, attempt `UPDATE`/`DELETE`/`TRUNCATE` on `audit_log` and assert each is rejected — this can only be verified against real Postgres grants, not a mock (rule #3).

## 3. Frontend — Vitest + React Testing Library

- `hooks/useAuth.ts`: login success stores token and updates state; failed login surfaces error; logout clears state; token refresh on 401.
- `api/client.ts`: fetch wrapper attaches Bearer token; 401 response triggers refresh-or-redirect-to-login; non-2xx response surfaces a typed error.
- `api/{accounts,auth,members}.ts`: each function calls the right URL/method/body shape (mock `fetch`).
- `pages/Login.tsx`: Zod validation rejects malformed email/short password before submit; submit calls the auth API; error response renders an inline error.
- `pages/Setup.tsx`, `pages/Members.tsx`, `pages/Accounts.tsx`: form submission happy path + validation rejection paths; primary-only UI elements hidden/disabled for non-primary roles.
- `components/app/AppLayout.tsx`: renders nav appropriate to the current role from context.

## 4. Future phases (2-6) — already have acceptance criteria, turn each into a test

Every phase doc (`phase-2` through `phase-6`) already ends with a 10-item
"Acceptance criteria" list. Treat each numbered item as a integration-test
title 1:1 — they're already written in testable form (e.g. phase-3 AC#5 "GET
/api/v1/audit-log returns 403 for partner and dependent roles" is a complete
test case as written). Don't re-derive these; transcribe them into
`tests/integration/test_phase_N.py` as each phase is implemented.

Two acceptance criteria are currently **untestable as specified** and need
the underlying doc fixed before tests can be written against them:

- phase-4 AC#3/#4 (auto-detected income stream merge-not-duplicate, and
  manual-value preservation across re-detection) — no merge algorithm is
  described anywhere in `phase-4-fire-and-debt.md`. Resolve this in the doc
  first.

## 5. Coverage math

Current backend line count is small (Phase 0-1 only: `core/`, `db/models/`,
`services/{user,account,member,auth,setup}.py`, `api/v1/*`, `repositories/account.py`).
The unit + integration tests in sections 1-2 above touch every non-trivial
branch in every existing module — the main residual risk to 90% is
boilerplate (Pydantic schema files, SQLAlchemy model column declarations,
`router.py` route wiring) which contributes lines but no branches; exclude
pure-declaration files with `# pragma: no cover` sparingly or accept they'll
be covered for free by the integration tests that exercise the endpoints.
