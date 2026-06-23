# Architecture

## Services overview

```
┌─────────────────────────────────────────────────────────────────┐
│ docker compose stack (internal network: hearthledger_net)       │
│                                                                 │
│  ┌──────────────────┐        ┌─────────────────────────────┐   │
│  │  nginx (Alpine)  │        │  FastAPI backend             │   │
│  │  port 80 → host  │◄──────►│  Python 3.12 / asyncpg      │   │
│  │  serves: React   │        │  port 8000 (internal)        │   │
│  │  proxies: /api/* │        └────────────┬────────────────┘   │
│  └──────────────────┘                     │                     │
│                                    ┌──────┴──────┐             │
│                               ┌────▼────┐   ┌────▼────┐        │
│                               │Postgres │   │  Redis  │        │
│                               │   18    │   │    8    │        │
│                               │internal │   │internal │        │
│                               └─────────┘   └────┬────┘        │
│                                                  │             │
│                               ┌──────────────────▼──────────┐  │
│                               │  ARQ worker (same image as   │  │
│                               │  backend; imports, exports,  │  │
│                               │  backups, valuation refresh) │  │
│                               └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

Only port 80 is exposed to the host machine.

## docker-compose.yml structure

```yaml
services:
  db:
    image: postgres:18-alpine
    environment:
      POSTGRES_DB: hearthledger
      POSTGRES_USER: hearthledger
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./backend/db_init.sql:/docker-entrypoint-initdb.d/01_init.sql
    networks: [hearthledger_net]
    # No ports: — never expose to host

  redis:
    image: redis:8-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./redis/redis.conf:/etc/redis/redis.conf:ro
    networks: [hearthledger_net]
    # No ports: — never expose to host

  backend:
    build: ./backend
    env_file: .env
    depends_on: [db, redis]
    networks: [hearthledger_net]
    healthcheck:
      test:
        [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')",
        ]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s

  worker:
    build: ./backend
    command: python -m app.worker.main
    env_file: .env
    depends_on:
      backend:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./data/backups:/data/backups
    networks: [hearthledger_net]

  frontend:
    build: ./frontend
    networks: [hearthledger_net]

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on: [backend, frontend]
    networks: [hearthledger_net]

networks:
  hearthledger_net:
    driver: bridge
```

## nginx routing

```nginx
# /api/* → backend:8000
# /* → frontend static files (built React SPA)
```

All API routes are prefixed `/api/v1/`. The frontend is a single-page app;
nginx serves `index.html` for all non-API, non-asset paths (HTML5 history mode).

## Request lifecycle

```
Browser
  → nginx :80
    → if /api/* → proxy_pass backend:8000
      → FastAPI route handler
        → JWT middleware resolves VisibilityContext
          → calls service method
            → service calls AccountRepository.get_visible(ctx)  [for reads]
            → service writes via @audit-decorated method        [for writes]
              → DB commit
              → audit_log INSERT (post-commit)
        ← response (Pydantic schema)
    → else → serve frontend/dist/index.html or static asset
```

## Authentication flow

- Login: `POST /api/v1/auth/login` → returns `access_token` (JWT, 30min)
  and sets `refresh_token` httpOnly cookie (30 days).
- All authenticated endpoints: Bearer token in `Authorization` header.
- Token refresh: `POST /api/v1/auth/refresh` → reads httpOnly cookie,
  returns new access token. Implements refresh token rotation.
- Logout: `POST /api/v1/auth/logout` → clears httpOnly cookie,
  invalidates refresh token hash in DB.
- Executor re-auth: `POST /api/v1/auth/reauth` → accepts password,
  returns short-lived `reauth_token` (10 min) used only for executor exports.

## Background worker (ARQ)

Worker runs as a separate container using the same Docker image as the backend.
Entrypoint: `python -m app.worker.main`.

Registered task queues:

- `import_queue`: CSV/OFX/QFX import jobs
- `export_queue`: PDF and Excel export generation
- `backup_queue`: DB dump, encrypt, prune
- `valuation_queue`: real estate valuation API refresh

Scheduled tasks (cron via APScheduler inside the worker):

- Backup: `BACKUP_SCHEDULE` env var (default `0 2 * * *`)
- Valuation refresh: `RE_VALUATION_REFRESH_SCHEDULE` env var (default `0 3 * * 1`)

## RBAC summary

Three member roles enforced via `VisibilityContext` middleware:

| Role        | Individual accounts  | Joint accounts | Admin ops | Executor exports |
| ----------- | -------------------- | -------------- | --------- | ---------------- |
| `primary`   | All members'         | Yes            | Yes       | Yes (re-auth)    |
| `partner`   | Own only (+ granted) | Yes            | No        | No               |
| `dependent` | None                 | Read-only      | No        | No               |

See `docs/data-model.md` for the `account_access_grants` schema.
See `CLAUDE.md` rule #1 for enforcement mechanism.
