# Demo Quickstart

HearthLedger ships with a seed script that populates the system with three
fictitious US households — from a straightforward dual-income couple to a
high-net-worth LA family with three properties. Use it to explore every
feature without entering your own data.

> **Demo environments only.** The production architecture is one household per
> installation. Seeding all three households is valid for demos and testing;
> each user's JWT token scopes them to their own household automatically.

---

## Prerequisites

HearthLedger must already be running. If you haven't started it yet, follow
[Getting Started](getting-started.md) through step 4 (docker compose up) and
stop before the setup wizard — the seed script creates the households for you.

---

## Step 1 — Seed the demo data

Run this from the project root (PostgreSQL is inside Docker and only reachable
via `docker-compose exec`):

```bash
docker-compose exec backend python scripts/seed_demo_data.py --household all
```

The script generates roughly 30 months of transactions (January 2024 – June 2026) with deterministic random jitter. When it finishes it prints a summary:

```
=== HearthLedger Demo Data Summary ===

Household 1: Chen-Nakamura (Round Rock TX)
  Members: 2 | Accounts: 12 | Transactions: ~XXXX | Properties: 1
  Computed Net Worth: ~$898,900

Household 2: Okonkwo-Rivera (Naperville IL)
  Members: 4 | Accounts: 19 | Transactions: ~XXXX | Properties: 2
  Computed Net Worth: ~$3,407,800

Household 3: Whitfield-Torres (Brentwood LA)
  Members: 4 | Accounts: 25 | Transactions: ~XXXX | Properties: 3
  Computed Net Worth: ~$9,463,400
```

To seed a single household instead:

```bash
docker-compose exec backend python scripts/seed_demo_data.py --household 1
```

---

## Step 2 — Open the app and log in

Open `http://localhost` and sign in with any credential from the table below.
All accounts share the same password: **`HearthDemo1!`**

### Household 1 — Chen-Nakamura (Round Rock, TX)

_Dual-income couple, no dependents. Net worth ~$899K._

| Role    | Email                     | Password     |
| ------- | ------------------------- | ------------ |
| Primary | wei@chen-nakamura.local   | HearthDemo1! |
| Partner | priya@chen-nakamura.local | HearthDemo1! |

What this household demonstrates:

- Basic two-member RBAC (primary + partner)
- Budget vs. actuals across 19 categories
- FIRE scenario: "Target 55 FIRE" (Wei, age 55 retirement target)
- Debt payoff: RAV4 auto loan (avalanche, +$200/mo extra)
- Single primary residence with 10 quarterly valuations
- Seasonal spending (travel, holiday gifts, annual service contracts)

### Household 2 — Okonkwo-Rivera (Naperville, IL)

_Senior law partner + school district administrator, two teenage dependents. Net worth ~$3.4M._

| Role    | Email                       | Password     |
| ------- | --------------------------- | ------------ |
| Primary | darius@okonkwo-rivera.local | HearthDemo1! |
| Partner | carmen@okonkwo-rivera.local | HearthDemo1! |

> Dependents Emma and Noah have `household_members` records but no login
> credentials — they view joint accounts via RBAC, not via direct login.

What this household demonstrates:

- Four-member RBAC with dependent read-only access
- Long-term rental property (Evanston condo) with P&L reporting
- Rental income variability (two late payments over 30 months)
- 529 college savings accounts (tracked as investment accounts)
- Two FIRE scenarios: "Retire at 60" and "Aggressive FIRE at 55"
- Two debt payoff scenarios: VW ID.4 and Toyota RAV4 (avalanche, cascading)
- Carmen's defined-benefit pension income stream (IMRF, age 62 start)
- Illinois income and property tax patterns
- Budget history: `restaurants` budget increases from $550 → $650 in March 2025

### Household 3 — Whitfield-Torres (Brentwood, LA)

_Entertainment law firm founder + real estate development consultant, two dependents. Net worth ~$9.5M._

| Role    | Email                           | Password     |
| ------- | ------------------------------- | ------------ |
| Primary | ben@whitfield-torres.local      | HearthDemo1! |
| Partner | gabriela@whitfield-torres.local | HearthDemo1! |

> Sophia (adult dependent) has elevated `account_access_grants` to three joint
> accounts but no login credentials. Ethan has no grants beyond standard
> dependent joint-account visibility.

What this household demonstrates:

- Three real estate properties: primary residence, long-term rental duplex (Silver Lake), and vacation/STR rental (Palm Springs)
- Seasonal short-term rental income with one vacancy month
- HELOC tracking (`heloc` account type, interest-only payments)
- SEP-IRA (Gabriela's self-employment retirement account)
- Elevated access grant for an adult dependent (Sophia)
- Two FIRE scenarios: "Coast at 58 / Semi-Retirement" and "True FIRE Stress Test"
- High-income California spending patterns (millionaire's tax bracket)
- Property manager fee as percentage of STR income
- Annual lump-sum retirement contributions (SEP-IRA, profit-sharing 401k)
- Budget history: `restaurants` budget increases from $2,000 → $2,400 in June 2025

---

## Re-seeding

The seed script is idempotent within a fresh database. If you want to start
over, clear the data and re-seed:

```bash
# Stop the stack
docker-compose stop

# Remove the Postgres volume (destroys ALL data)
docker-compose rm -f db
docker volume rm financial-dashboard_postgres_data  # adjust name to match your compose project

# Start fresh
docker-compose up -d

# Wait ~30 seconds for migrations, then re-seed
docker-compose exec backend python scripts/seed_demo_data.py --household all
```

Or, to reset just the database without tearing down containers, connect to
PostgreSQL and truncate the relevant tables — but a full volume reset is
simpler and avoids foreign-key ordering issues.

---

## Related

- [Getting Started](getting-started.md) — install and run HearthLedger from scratch
- [User Guide](user-guide.md) — walkthrough of every feature
- [Demo Dataset Specification](hearthledger-demo-data-spec.md) — full data definitions (income patterns, accounts, FIRE scenarios) for all three households
