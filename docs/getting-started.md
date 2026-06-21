# Getting Started with HearthLedger

HearthLedger is a self-hosted household financial tracking system. It runs entirely on your own machine inside Docker — nothing is sent to the cloud.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)
- Git
- A terminal

## 1. Clone the repository

```bash
git clone https://github.com/jdmacleod/financial-dashboard.git hearthledger
cd hearthledger
```

## 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder values:

**Generate `SECRET_KEY`** (JWT signing key):

```bash
openssl rand -hex 32
```

**Generate `SECRET_ENCRYPTION_KEY`** (AES-256-GCM field encryption key):

```bash
python3 -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

**Set `DB_PASSWORD`** to any strong password.

Minimum `.env` for a first run:

```bash
DATABASE_URL=postgresql+asyncpg://hearthledger:yourpassword@db:5432/hearthledger # pragma: allowlist secret
DB_PASSWORD=yourpassword
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<64-char hex from openssl>
SECRET_ENCRYPTION_KEY=<32-byte base64 from python>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15
RE_VALUATION_PROVIDER=manual
RE_VALUATION_API_KEY=
RE_VALUATION_REFRESH_SCHEDULE=0 3 * * 1
BACKUP_PATH=/data/backups
BACKUP_RETENTION_DAYS=30
BACKUP_SCHEDULE=0 2 * * *
EXPORT_PATH=/data/exports
ALLOWED_ORIGINS=http://localhost,http://localhost:80
```

## 3. Create the data directories

```bash
mkdir -p data/postgres data/backups data/exports
```

## 4. Start the stack

```bash
docker compose up -d
```

This starts six services:

- `db` — PostgreSQL 18
- `redis` — Redis 8
- `backend` — FastAPI application
- `worker` — ARQ background job worker
- `frontend` — React/Vite build
- `nginx` — Reverse proxy on port 80

Wait about 20–30 seconds for PostgreSQL to initialize and Alembic migrations to run.

Check that everything is healthy:

```bash
docker compose ps
```

All six services should show `Up`.

## 5. Run the setup wizard

Open your browser to `http://localhost`.

On first launch HearthLedger detects that no household exists and redirects you to the setup page. Fill in:

- **Household name** — e.g. "Smith Family"
- **Your name** — e.g. "Alex"
- **Email** — your login email
- **Password** — choose a strong password

Click **Create household**. You are automatically logged in as the Primary member.

## 6. Add your first account

Click **Accounts** in the sidebar. The page shows five category groups:
Banking & Cash, Retirement, Investments, Real estate, and Liabilities. Click
the **+** on the category that matches your account.

For a first account, click **+** on **Banking & Cash** and fill in:

- **Nickname** — e.g. "Chase Checking"
- **Type** — `checking`, `savings`, or `other_asset`
- **Institution** — e.g. "Chase Bank"

Click **Save**. Your account appears in the Banking & Cash group.

> **Note:** Institution names and account numbers are stored encrypted
> (AES-256-GCM). They never appear in plaintext in the database.

For all account types and categories, see [How to add accounts](howto-add-accounts.md).

## 7. Import transactions

From the **Transactions** page for an account, click **Import**. HearthLedger accepts:

- **CSV** — exported from your bank (Chase, Bank of America, Fidelity, and most others)
- **OFX/QFX** — Quicken/Microsoft Money format

The import runs as a background job. Refresh the page after a few seconds to see your transactions.

## 8. Check the dashboard

Go to the **Dashboard**. Once you have transactions and accounts, you'll see:

- KPI cards: net worth, MTD income, MTD expenses, savings rate
- Budget alerts (if you've set budgets)
- Net worth chart (12 months)
- Spending by category chart

## Stopping and restarting

```bash
# Stop without losing data
docker compose stop

# Start again
docker compose start

# Destroy containers (data volume is preserved in ./data)
docker compose down
```

## Upgrading

```bash
git pull
docker compose build
docker compose up -d
```

Alembic migrations run automatically on backend startup.

## Logs

```bash
docker compose logs backend     # API logs
docker compose logs worker      # Background job logs
docker compose logs nginx       # Access logs
```

## Next steps

- [Demo Quickstart](demo-quickstart.md) — load three sample households and explore all features with real data
- [User Guide](user-guide.md) — all features explained
- [API Reference](api-reference.md) — REST API documentation
- [Security](security.md) — how authentication and encryption work
