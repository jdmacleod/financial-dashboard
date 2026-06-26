# Demo Quickstart

HearthLedger ships with a seed script that populates the system with seven
fictitious US households, ranging from a single early-career Atlanta saver
digging out of consumer debt to a widowed Westchester County retiree with a
full estate-planning stack. Use it to explore every feature without entering
your own data.

> **Demo environments only.** The production architecture is one household per
> installation. Seeding all seven households is valid for demos and testing;
> each user's JWT token scopes them to their own household automatically.

---

## Prerequisites

HearthLedger must already be running. If you haven't started it yet, follow
[Getting Started](getting-started.md) through step 4 (docker compose up) and
stop before the setup wizard: the seed script creates the households for you.

---

## Step 1: Seed the demo data

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
  Computed Net Worth: ~$1,003,300

Household 2: Okonkwo-Rivera (Naperville IL)
  Members: 4 | Accounts: 19 | Transactions: ~XXXX | Properties: 2
  Computed Net Worth: ~$3,620,400

Household 3: Whitfield-Torres (Brentwood CA)
  Members: 4 | Accounts: 29 | Transactions: ~XXXX | Properties: 3
  Computed Net Worth: ~$9,902,500

Household 4: Park-Cole (Nashville TN)
  Members: 2 | Accounts: 14 | Transactions: ~XXXX | Properties: 0
  Computed Net Worth: ~$300,100

Household 5: Langford (Sarasota FL)
  Members: 2 | Accounts: 17 | Transactions: ~XXXX | Properties: 2
  Computed Net Worth: ~$13,327,100

Household 6: Castellano (Scarsdale NY)
  Members: 1 | Accounts: 17 | Transactions: ~XXXX | Properties: 2
  Computed Net Worth: ~$18,290,000

Household 7: Brooks (Atlanta GA)
  Members: 1 | Accounts: 9 | Transactions: ~XXXX | Properties: 0
  Computed Net Worth: ~$12,200
```

To seed a single household instead:

```bash
docker-compose exec backend python scripts/seed_demo_data.py --household 1
```

---

## Step 2: Open the app and log in

Open `http://localhost` and sign in with any credential from the table below.
All accounts share the same password: **`HearthDemo1!`**

### Household 1: Chen-Nakamura (Round Rock, TX)

_Dual-income couple, no dependents. Net worth ~$1.0M._

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

### Household 2: Okonkwo-Rivera (Naperville, IL)

_Senior law partner + school district administrator, two teenage dependents. Net worth ~$3.6M._

| Role    | Email                       | Password     |
| ------- | --------------------------- | ------------ |
| Primary | darius@okonkwo-rivera.local | HearthDemo1! |
| Partner | carmen@okonkwo-rivera.local | HearthDemo1! |

> Dependents Emma and Noah have `household_members` records but no login
> credentials: they view joint accounts via RBAC, not via direct login.

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

### Household 3: Whitfield-Torres (Brentwood, CA)

_Entertainment law firm founder + real estate development consultant, two dependents. Net worth ~$9.9M._

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

### Household 4: Park-Cole (East Nashville, TN)

_Late-20s dual-income renters. Net worth ~$300K._

| Role    | Email                  | Password     |
| ------- | ---------------------- | ------------ |
| Primary | zoe@park-cole.local    | HearthDemo1! |
| Partner | marcus@park-cole.local | HearthDemo1! |

What this household demonstrates:

- Aggressive debt avalanche: three simultaneous loans (student, Honda auto, personal)
- Named savings-goal brokerage account (House Fund for future down payment)
- Renter expense patterns: rent, renters insurance, no mortgage
- FIRE scenario: "FIRE by 45" on a combined ~$157K income
- Zoe's student loan income-driven cascade (payment increases after grace period ends)
- Nashville cost-of-living spending patterns

### Household 5: Langford (Sarasota, FL)

_Retired couple; SS + pension + RMDs + LLC income. Net worth ~$13.3M._

| Role    | Email                 | Password     |
| ------- | --------------------- | ------------ |
| Primary | bob@langford.local    | HearthDemo1! |
| Partner | maggie@langford.local | HearthDemo1! |

What this household demonstrates:

- Multiple retirement income streams: Social Security, defined-benefit pension, quarterly RMDs
- Part-time LLC consulting income (Maggie's HR business)
- Two real estate properties: Sarasota primary home (cash purchase, no mortgage) and Highlands NC vacation home (30-year mortgage)
- Short-term rental income from Highlands NC property
- Null-mortgage equity path: primary residence has no linked mortgage account
- Medicare/Medigap healthcare expense patterns
- Florida retirement spending (no state income tax, high property tax)
- Required Minimum Distributions from traditional IRA (quarterly schedule)

---

### Household 6: Castellano (Scarsdale, NY)

_Widowed retiree; full estate-and-legacy stack. Net worth ~$18.3M._

| Role    | Email                 | Password     |
| ------- | --------------------- | ------------ |
| Primary | rosa@castellano.local | HearthDemo1! |

What this household demonstrates:

- Single-member household: one primary principal, full visibility, no access grants
- Revocable trust titling on accounts
- ILIT-owned permanent life insurance policy (outside personal net worth and the taxable estate)
- Charitable remainder unitrust (CRT) and donor-advised fund (DAF), both excluded from personal net worth
- Legacy concentrated stock position with stepped-up basis
- Inherited IRA on the SECURE Act 10-year distribution clock
- Private-equity capital commitment with capital calls
- Revolving SBLOC (securities-backed line of credit)
- Single decumulation FIRE scenario

---

### Household 7: Brooks (Atlanta, GA)

_Single early-career saver, top income-for-age but low net worth, digging out of consumer debt. Net worth ~$12K._

| Role    | Email                | Password     |
| ------- | -------------------- | ------------ |
| Primary | aaliyah@brooks.local | HearthDemo1! |

What this household demonstrates:

- Single-member household: one primary principal, full visibility, no access grants
- Early-accumulation lifecycle opener: high income-for-age, deliberately low (and near-breakeven) net worth — the rung below Park-Cole
- Debt elimination as the hero: three simultaneous balances — Chase credit card (21%, ~$9K), SoFi personal loan (11%, ~$4K), MOHELA federal student loan (6%, ~$40K)
- Avalanche vs. snowball payoff orders that actually diverge: avalanche-by-rate targets the card first, snowball-by-balance targets the personal loan first, so the "Avalanche saves $X" callout renders
- Roth-heavy retirement (Roth 401k + Roth IRA) — contributing in a low bracket now
- HSA invested for the triple-tax benefit (young HDHP saver, payroll-funded)
- FIRE scenario: "Financial Independence by 50"
- Debit-funded variable spending (debt-payoff mode — not adding to the card)

---

## Re-seeding

### Check current state

Before resetting anything, inspect what's in the database:

```bash
docker-compose exec backend python scripts/seed_demo_data.py --action inspect
```

Output:

```
=== HearthLedger Demo DB State ===

  #    Name                      Members  Accounts  Transactions  Status
  -------------------------------------------------------------------
  1    Chen-Nakamura                   2        12         3,124  SEEDED
  2    Okonkwo-Rivera                  4        19         4,871  SEEDED
  3    Whitfield-Torres                4        29         6,390  SEEDED
  4    Park-Cole                       2        14         2,241  SEEDED
  5    Langford                        2        17         2,188  SEEDED
  6    Castellano                      1        17        ~2,000  SEEDED
  7    Brooks                          1         9        ~2,000  SEEDED
```

### Reset a single household (targeted)

Delete and immediately re-seed one household without touching the others:

```bash
docker-compose exec backend python scripts/seed_demo_data.py \
  --household 5 --action reset
```

The delete and reseed run in a single transaction; if the reseed fails, the
delete is rolled back and the household is restored. Add `--yes` to skip the
confirmation prompt (useful in scripts).

### Delete a household without reseeding

```bash
docker-compose exec backend python scripts/seed_demo_data.py \
  --household 5 --action delete
```

### Full reset (nuclear option)

Use this when you want a completely clean database: for example, after a
schema migration that changes existing tables.

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

---

## Related

- [Getting Started](getting-started.md): install and run HearthLedger from scratch
- [User Guide](user-guide.md): walkthrough of every feature
- [Demo Dataset Specification](hearthledger-demo-data-spec.md): full data definitions (income patterns, accounts, FIRE scenarios) for H1–H3
- [Demo Dataset Specification: Revised](hearthledger-demo-data-spec-revised.md): expanded spec incorporating H4 and H5 alongside H1–H3
- [Phase 11 Design Doc](phase-11-demo-households-h4-h5.md): H4 Park-Cole and H5 Langford implementation spec
