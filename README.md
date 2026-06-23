# HearthLedger

[![CI](https://github.com/jdmacleod/financial-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/jdmacleod/financial-dashboard/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jdmacleod/financial-dashboard/graph/badge.svg)](https://codecov.io/gh/jdmacleod/financial-dashboard)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Node 26](https://img.shields.io/badge/node-26-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.137+-009688.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed.svg)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Self-hosted household financial tracking. Runs entirely on your own machine — no cloud, no subscriptions.

## Features

- **Accounts**: checking, savings, credit, HSA, mortgage, and loans (transaction accounts)
- **Assets**: real estate (valuations), pensions (present-value estimate), and investment/retirement accounts (balance snapshots) on a dedicated page
- **Transactions**: manual entry, edit, and delete; CSV and OFX/QFX import; bulk categorize; duplicate detection
- **Budgets**: monthly limits per category with dashboard alerts
- **Reports**: net worth (with pension present-value annotations), cash flow (with a Social Security / pension / RMD retirement-income breakdown), investments (top positions + holdings mix by asset class), spending by category, budget vs actuals, property P&L
- **FIRE planning**: retirement projections with multiple income streams and scenario modeling; auto-detects vested pension income
- **Debt payoff**: avalanche/snowball comparison with extra payment modeling
- **Real estate**: property type selection (primary, rental, vacation, commercial, land); manual or API-driven valuations (ATTOM, Estated)
- **Exports**: PDF and Excel reports with executor re-authentication gate
- **Backups**: scheduled and manual database backups, AES-256-GCM encrypted
- **Multi-member**: primary + partner + dependent roles with per-account access grants
- **Dark mode**: system, light, or dark; per-member dashboard layout customization

## Quickstart

**Prerequisites:** Docker Desktop, Git

```bash
git clone https://github.com/jdmacleod/financial-dashboard.git
cd financial-dashboard
cp .env.example .env
```

Edit `.env` and set three values:

```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=...

# Generate with: python3 -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
SECRET_ENCRYPTION_KEY=...

DB_PASSWORD=choose-a-strong-password
```

Then:

```bash
mkdir -p data/postgres data/backups
docker compose up -d
```

Open `http://localhost` and complete the setup wizard (household name, your name, email, password).

See [docs/getting-started.md](docs/getting-started.md) for the full walkthrough.

## Try it with demo data

Once the stack is running, load five pre-built households — 30 months of
realistic transactions, budgets, FIRE scenarios, and real estate:

```bash
docker-compose exec backend python scripts/seed_demo_data.py --household all
```

Open `http://localhost` and sign in. Password is `HearthDemo1!` for all demo accounts:

| Household             | Email                       | Net Worth |
| --------------------- | --------------------------- | --------- |
| Chen-Nakamura (TX)    | wei@chen-nakamura.local     | ~$899K    |
| Okonkwo-Rivera (IL)   | darius@okonkwo-rivera.local | ~$3.4M    |
| Whitfield-Torres (LA) | ben@whitfield-torres.local  | ~$9.5M    |
| Park-Cole (TN)        | zoe@park-cole.local         | ~$155K    |
| Langford (FL)         | bob@langford.local          | ~$12.9M   |

See [docs/demo-quickstart.md](docs/demo-quickstart.md) for all ten credentials and what each household exercises.

## Stack

| Layer           | Technology                                                                      |
| --------------- | ------------------------------------------------------------------------------- |
| API             | Python 3.12, FastAPI 0.137+, SQLAlchemy 2 async, Pydantic v2                    |
| Database        | PostgreSQL 18                                                                   |
| Background jobs | ARQ (Redis 8), APScheduler                                                      |
| Frontend        | React 19, TypeScript, Vite 8, TanStack Query/Router, Tailwind CSS v4, shadcn/ui |
| Proxy           | nginx (Alpine)                                                                  |
| Deployment      | Docker Compose                                                                  |

## Documentation

- [Getting Started](docs/getting-started.md): install, configure, first run
- [Demo Quickstart](docs/demo-quickstart.md): seed demo data and explore with sample households
- [User Guide](docs/user-guide.md): all features
- [Tutorial: portfolio and retirement insights](docs/tutorial-portfolio-and-retirement-insights.md): positions, retirement income, and pension PV on demo data
- How-to guides: [investment positions](docs/howto-view-investment-positions.md), [retirement income](docs/howto-track-retirement-income.md), [pension present value](docs/howto-set-pension-present-value.md), [adding accounts](docs/howto-add-accounts.md)
- [Why pension present value works this way](docs/explanation-pension-present-value.md): the valuation model and estimate history
- [API Reference](docs/api-reference.md): REST API
- [Security](docs/security.md): auth, encryption, audit log
- [Contributing](CONTRIBUTING.md): dev setup, pre-commit hooks, running tests

## License

MIT
