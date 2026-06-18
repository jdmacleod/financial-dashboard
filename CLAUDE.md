# HearthLedger — Claude Code Project Context

Household financial tracking system. Locally hosted, browser-accessible,
open source (MIT). Single household per installation.

Full design rationale and amendment history live in `docs/`. Read the
relevant phase doc before starting any implementation work.

---

## Tech stack (exact versions)

### Backend

- Python 3.12
- uv (dependency management — not pip directly)
- FastAPI 0.115+
- SQLAlchemy 2.x async (asyncpg driver)
- Alembic (migrations)
- Pydantic v2
- python-jose[cryptography] (JWT)
- passlib[bcrypt] (password hashing)
- cryptography (AES-256-GCM field encryption)
- ofxparse (OFX/QFX import)
- openpyxl (Excel export)
- WeasyPrint (PDF export)
- ARQ (async Redis task queue)
- APScheduler (cron scheduling inside ARQ worker)

### Frontend

- Node 20 LTS
- React 18 + TypeScript (strict mode)
- Vite 5
- TanStack Query v5
- TanStack Router v1
- Tailwind CSS v3
- shadcn/ui
- Recharts
- React Hook Form + Zod
- date-fns

### Infrastructure

- PostgreSQL 16 (Docker)
- Redis 7 (Docker)
- nginx (Alpine, Docker — serves built frontend + proxies API)

---

## Repository layout

```
hearthledger/
├── CLAUDE.md
├── docker-compose.yml
├── docker-compose.override.yml.example
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── api/
│       │   └── v1/
│       │       ├── router.py
│       │       ├── auth.py
│       │       ├── members.py
│       │       ├── accounts.py
│       │       ├── transactions.py
│       │       ├── categories.py
│       │       ├── budgets.py
│       │       ├── snapshots.py
│       │       ├── imports.py
│       │       ├── exports.py
│       │       ├── reports.py
│       │       ├── fire.py
│       │       └── backups.py
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py       # JWT, bcrypt
│       │   ├── encryption.py     # AES-256-GCM field encryption
│       │   ├── audit.py          # @audit decorator + AuditRepository
│       │   └── visibility.py     # VisibilityContext + account filter
│       ├── db/
│       │   ├── base.py           # SQLAlchemy Base, engine, session
│       │   └── models/
│       │       ├── household.py
│       │       ├── member.py
│       │       ├── user.py
│       │       ├── account.py
│       │       ├── transaction.py
│       │       ├── category.py
│       │       ├── budget.py
│       │       ├── snapshot.py
│       │       ├── real_estate.py
│       │       ├── debt.py
│       │       ├── fire.py
│       │       ├── import_job.py
│       │       ├── export_job.py
│       │       ├── backup_job.py
│       │       ├── access_grant.py
│       │       └── audit_log.py
│       ├── repositories/
│       │   ├── account.py        # AccountRepository (visibility-aware)
│       │   ├── transaction.py
│       │   ├── audit.py          # append-only AuditRepository
│       │   └── ...
│       ├── services/
│       │   ├── auth.py
│       │   ├── member.py
│       │   ├── account.py
│       │   ├── transaction.py
│       │   ├── import_service.py
│       │   ├── export_service.py
│       │   ├── fire_detector.py
│       │   ├── fire_projector.py
│       │   ├── backup.py
│       │   └── valuation/
│       │       ├── base.py
│       │       ├── attom.py
│       │       ├── estated.py
│       │       └── manual.py
│       ├── importers/
│       │   ├── csv_importer.py
│       │   └── ofx_importer.py
│       ├── exporters/
│       │   ├── pdf_exporter.py
│       │   └── excel_exporter.py
│       ├── schemas/
│       │   └── ...               # Pydantic request/response models
│       └── worker/
│           ├── main.py           # ARQ worker entry point
│           └── tasks/
│               ├── import_tasks.py
│               ├── export_tasks.py
│               ├── backup_tasks.py
│               └── valuation_tasks.py
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── components.json           # shadcn/ui config
│   └── src/
│       ├── main.tsx
│       ├── router.tsx
│       ├── api/                  # typed API client (fetch wrappers)
│       ├── components/
│       │   ├── ui/               # shadcn/ui primitives
│       │   └── app/              # application components
│       ├── pages/
│       ├── hooks/
│       ├── stores/               # Zustand stores (UI state only)
│       └── lib/
│           ├── formatters.ts     # currency, date, number formatting
│           └── utils.ts
├── nginx/
│   └── nginx.conf
└── data/                         # gitignored — Docker volume mounts
    ├── postgres/
    └── backups/
```

---

## Non-negotiable architectural rules

These are hard constraints. Do not work around them.

**1. All account queries go through `AccountRepository.get_visible(ctx)`.**
No route handler, service, or task may query the `accounts` table directly
without going through this method. The `VisibilityContext` (resolved from
the JWT in every authenticated request) encapsulates all RBAC rules.
A direct account query in a route handler is a security gap.

**2. All data mutations go through service methods decorated with `@audit`.**
Route handlers call service methods. They do not write to the database
directly. The `@audit` decorator fires after a successful commit and writes
to `audit_log`. Any service method that mutates data without `@audit` will
produce silent audit gaps.

**3. The `audit_log` table is append-only at the DB permission level.**
The application's Postgres role (`hearthledger_app`) has only
`SELECT, INSERT` on `audit_log` — no `UPDATE`, no `DELETE`, no `TRUNCATE`.
This is enforced in the baseline migration, not just by convention.
Never grant additional privileges to this table.

**4. Encrypted fields never appear in the audit log.**
`institution_name_enc`, `account_number_enc`, `routing_number_enc`,
`address_enc`, and `notes_enc` are never written to `audit_log.previous_value`
or `audit_log.new_value` — not even in encrypted form.

**5. The `.env` file is never committed.**
`.env` is in `.gitignore`. `.env.example` contains only placeholder values
and is the only committed secrets-adjacent file. The `data/` directory
(Postgres volume mount) is also gitignored.

**6. No plaintext PII in the database.**
Account numbers, institution names, routing numbers, property addresses,
and account notes are always stored as `BYTEA` via AES-256-GCM. The
encryption key comes from `SECRET_ENCRYPTION_KEY` in `.env`. Decryption
happens in the application layer at read time.

**7. Only port 80 is exposed to the host.**
PostgreSQL (5432) and Redis (6379) ports are internal to the Docker
network only. Never expose them in `docker-compose.yml`.

---

## Environment variables (full list)

All defined in `.env`, documented in `.env.example`.

```bash
# Database
DATABASE_URL=postgresql+asyncpg://hearthledger:password@db:5432/hearthledger  # pragma: allowlist secret

# Redis / worker
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=<random 64-char hex>               # JWT signing
SECRET_ENCRYPTION_KEY=<random 32-byte base64> # AES-256-GCM field encryption
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Auth hardening
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15

# Real estate valuation
RE_VALUATION_PROVIDER=manual                  # manual | attom | estated
RE_VALUATION_API_KEY=
RE_VALUATION_REFRESH_SCHEDULE=0 3 * * 1      # cron; weekly Monday 3am

# Backup
BACKUP_PATH=/data/backups
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *                     # cron; daily 2am

# CORS (lock to localhost in production)
ALLOWED_ORIGINS=http://localhost,http://localhost:80
```

---

## Coding conventions

- **Async throughout.** All DB operations use `async with session` and
  `await`. No synchronous SQLAlchemy calls.
- **UUID primary keys everywhere.** Use `uuid.uuid4()` as Python-side default.
  Type: `UUID` in SQLAlchemy, `uuid` in Postgres.
- **`TIMESTAMPTZ` for all timestamps.** Never `TIMESTAMP WITHOUT TIME ZONE`.
- **Pydantic v2 models for all request/response schemas.** No raw dicts
  crossing the API boundary.
- **TypeScript strict mode.** No `any`. API response types are generated or
  manually maintained in `src/api/types.ts`.
- **All currency values are `Decimal` in Python, `NUMERIC(18,4)` in Postgres,
  and formatted with `Intl.NumberFormat` in the frontend.** Never `float` for
  money.
- **USD only (v1).** No multi-currency logic, no FX tables.
- **ISO 8601 dates in filenames.** Colons replaced with hyphens for filesystem
  compatibility: `2025-01-15T02-00-00Z`, not `2025-01-15T02:00:00Z`.

---

## Testing requirements

### Backend (pytest + pytest-asyncio)

- Unit tests for all service methods
- Unit tests for `VisibilityContext` permission logic (all role/account-type combinations)
- Unit tests for `@audit` decorator (verify log rows written, verify encrypted fields excluded)
- Unit tests for FIRE projection engine
- Integration tests for all API endpoints (use `httpx.AsyncClient` against a test DB)
- Import tests: CSV and OFX/QFX round-trip with sample fixture files

### Frontend (Vitest + React Testing Library)

- Component tests for all form components
- Hook tests for `useAuth`, `useVisibility`
- API client tests (mock fetch)

---

## Design review checklist (run before each phase PR)

- [ ] No raw account queries outside `AccountRepository.get_visible()`
- [ ] All mutating service methods have `@audit` decorator
- [ ] No encrypted field values in audit log entries
- [ ] No new environment secrets missing from `.env.example`
- [ ] All `TIMESTAMPTZ` — no naive timestamps
- [ ] No `float` used for monetary values
- [ ] All new DB columns have Alembic migration
- [ ] Migration is reversible (has `downgrade()` implementation)
- [ ] New API endpoints have Pydantic request and response schemas
- [ ] New API endpoints are covered by integration tests

---

## gstack

Use the `/browse` skill from gstack for all web browsing. Never use
`mcp__claude-in-chrome__*` tools.

Available gstack skills:

- `/office-hours`
- `/plan-ceo-review`
- `/plan-eng-review`
- `/plan-design-review`
- `/design-consultation`
- `/design-shotgun`
- `/design-html`
- `/review`
- `/ship`
- `/land-and-deploy`
- `/canary`
- `/benchmark`
- `/browse`
- `/connect-chrome`
- `/qa`
- `/qa-only`
- `/design-review`
- `/setup-browser-cookies`
- `/setup-deploy`
- `/setup-gbrain`
- `/retro`
- `/investigate`
- `/document-release`
- `/document-generate`
- `/codex`
- `/cso`
- `/autoplan`
- `/plan-devex-review`
- `/devex-review`
- `/careful`
- `/freeze`
- `/guard`
- `/unfreeze`
- `/gstack-upgrade`
- `/learn`
