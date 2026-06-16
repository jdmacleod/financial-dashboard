# Phase 0 — Infrastructure

Stand up the complete Docker Compose stack with all services running,
the database initialized with the full schema, and an empty but
functional development environment. No business logic is implemented
in this phase.

---

## Deliverables

- [ ] Repository scaffolded with correct directory structure (see CLAUDE.md)
- [ ] `docker-compose.yml` with all five services
- [ ] `.env.example` documenting every environment variable
- [ ] `.gitignore` excluding `.env`, `data/`, `__pycache__`, `node_modules`, `dist/`
- [ ] FastAPI app skeleton running and reachable at `http://localhost/api/v1/health`
- [ ] React + Vite skeleton served at `http://localhost/`
- [ ] Alembic configured and baseline migration applied
- [ ] All tables created per `docs/data-model.md`
- [ ] `hearthledger_app` Postgres role created with restricted `audit_log` permissions
- [ ] ARQ worker running (no tasks registered yet; just the worker process)
- [ ] Redis reachable from both backend and worker containers
- [ ] Backup volume mounted and writable from worker container

---

## Step-by-step

### 1. Git repository

```bash
git init hearthledger
cd hearthledger
```

Create `.gitignore`:
```
.env
data/
__pycache__/
*.pyc
*.pyo
.venv/
node_modules/
dist/
.DS_Store
*.dump
*.dump.enc
```

### 2. Docker Compose

`docker-compose.yml` — see `docs/architecture.md` for the full structure.

`docker-compose.override.yml.example`:
```yaml
# Copy to docker-compose.override.yml for local development.
# Enables hot-reload for backend and frontend.
services:
  backend:
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0 --port 5173
```

### 3. Environment variables

`.env.example`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://hearthledger:changeme@db:5432/hearthledger
DB_PASSWORD=changeme

# Redis / worker
REDIS_URL=redis://redis:6379/0

# Security — generate with: openssl rand -hex 32
SECRET_KEY=replace_with_64_char_hex_string
# Generate with: python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
SECRET_ENCRYPTION_KEY=replace_with_32_byte_base64_string

ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Auth hardening
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15

# Real estate valuation
RE_VALUATION_PROVIDER=manual
RE_VALUATION_API_KEY=
RE_VALUATION_REFRESH_SCHEDULE=0 3 * * 1

# Backup
BACKUP_PATH=/data/backups
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *

# CORS
ALLOWED_ORIGINS=http://localhost,http://localhost:80
```

### 4. Backend skeleton

`backend/pyproject.toml`:
```toml
[project]
name = "hearthledger-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "pydantic[email]>=2.0",
    "pydantic-settings>=2.0",
    "python-jose[cryptography]>=3.3",
    "passlib[bcrypt]>=1.7",
    "cryptography>=42",
    "ofxparse>=0.21",
    "openpyxl>=3.1",
    "weasyprint>=62",
    "arq>=0.25",
    "apscheduler>=3.10",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "pytest-cov>=5",
]
```

`backend/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv
COPY pyproject.toml .
RUN uv pip install --system -e .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/app/main.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import router

app = FastAPI(title="HearthLedger API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

`backend/app/core/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    secret_key: str
    secret_encryption_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    re_valuation_provider: str = "manual"
    re_valuation_api_key: str = ""
    re_valuation_refresh_schedule: str = "0 3 * * 1"
    backup_path: str = "/data/backups"
    backup_retention_days: int = 30
    backup_schedule: str = "0 2 * * *"
    allowed_origins: list[str] = ["http://localhost"]

settings = Settings()
```

### 5. Database initialization

`backend/db_init.sql` — runs once on first Postgres container start:
```sql
-- Create restricted application role
CREATE ROLE hearthledger_app LOGIN PASSWORD 'changeme';
GRANT CONNECT ON DATABASE hearthledger TO hearthledger_app;
GRANT USAGE ON SCHEMA public TO hearthledger_app;
-- Table-level grants are applied per-table in Alembic migrations.
-- The audit_log table will receive only SELECT, INSERT.
```

### 6. SQLAlchemy + Alembic

`backend/app/db/base.py`:
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

`backend/alembic.ini` — standard Alembic config pointing to
`app/db/base.py:Base.metadata` and using async env.

`backend/alembic/env.py` — use `run_async_migrations()` pattern
for asyncpg compatibility.

#### Baseline migration

`alembic/versions/0001_baseline.py`

Create all tables per `docs/data-model.md` in dependency order:

1. `households`
2. `household_members`
3. `users`
4. `categories`
5. `accounts`
6. `account_access_grants`
7. `account_snapshots`
8. `real_estate_properties`
9. `property_valuations`
10. `debts`
11. `transactions` (depends on `real_estate_properties` for FK)
12. `budgets`
13. `fire_scenarios`
14. `import_jobs`
15. `export_jobs`
16. `backup_jobs`
17. `audit_log`

After creating `audit_log`, execute:
```sql
REVOKE ALL ON audit_log FROM hearthledger_app;
GRANT SELECT, INSERT ON audit_log TO hearthledger_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO hearthledger_app;
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM hearthledger_app;
```

Also seed system categories (see `docs/data-model.md` category list).
The seeded rows use a fixed household_id placeholder of
`00000000-0000-0000-0000-000000000000` — they are copied to each real
household when it is first created (see Phase 1).

Migration must have a working `downgrade()` that drops all tables in
reverse dependency order.

### 7. Frontend skeleton

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss @tailwindcss/vite
npm install @tanstack/react-query @tanstack/react-router
npm install react-hook-form @hookform/resolvers zod
npm install recharts date-fns
npx shadcn@latest init
```

`frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
```

### 8. nginx config

`nginx/nginx.conf`:
```nginx
events {}
http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    server {
        listen 80;

        location /api/ {
            proxy_pass         http://backend:8000;
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
        }

        location / {
            root   /usr/share/nginx/html;
            index  index.html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

### 9. ARQ worker skeleton

`backend/app/worker/main.py`:
```python
import asyncio
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings

async def startup(ctx):
    pass  # DB session pool will be added in Phase 1

async def shutdown(ctx):
    pass

class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions = []  # tasks registered per phase

if __name__ == "__main__":
    from arq import run_worker
    run_worker(WorkerSettings)
```

---

## Acceptance criteria

All of the following must pass before Phase 0 is complete:

1. `docker compose up --build` completes without errors.
2. `curl http://localhost/api/v1/health` returns `{"status": "ok"}`.
3. `curl http://localhost/` returns the React app HTML shell.
4. `docker compose exec backend alembic current` shows the baseline migration as head.
5. `docker compose exec db psql -U hearthledger -c "\dt"` lists all 17 tables.
6. `docker compose exec db psql -U hearthledger -c "\dp audit_log"` shows
   that `hearthledger_app` has only SELECT and INSERT (no UPDATE/DELETE).
7. Worker container is running: `docker compose ps worker` shows `Up`.
8. Redis is reachable from both backend and worker:
   `docker compose exec backend python -c "import arq; print('ok')"` passes.
9. `data/` directory exists on the host and is gitignored.
10. `.env` is not tracked: `git status` does not show `.env`.
