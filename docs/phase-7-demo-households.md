# Phase 7 — Demo Households & Seed Script

Creates a deterministic seed script that populates HearthLedger with three
fictitious households of increasing financial complexity. The seed data is the
primary vehicle for live demos, integration testing, and exercising every
major feature surface in a single command.

Source spec: `docs/hearthledger-demo-data-spec.md`

---

## Status

**Complete** — v0.7.0.0

---

## Deliverables

- [x] `backend/scripts/seed_demo_data.py` — entry point (`--household 1|2|3|all`)
- [x] `backend/scripts/seed_households/__init__.py`
- [x] `backend/scripts/seed_households/shared_categories.py` — full category taxonomy
- [x] `backend/scripts/seed_households/h1_chen_nakamura.py`
- [x] `backend/scripts/seed_households/h2_okonkwo_rivera.py`
- [x] `backend/scripts/seed_households/h3_whitfield_torres.py`
- [x] Migration 0005: `heloc` added to `account_type` enum
- [x] Migration 0005: nullable `member_id` FK added to `fire_scenarios`

---

## Households at a glance

| #   | Name             | Location       | Members                                  | Accounts | Properties | Net Worth |
| --- | ---------------- | -------------- | ---------------------------------------- | -------- | ---------- | --------- |
| 1   | Chen-Nakamura    | Round Rock, TX | 2                                        | 12       | 1          | ~$899K    |
| 2   | Okonkwo-Rivera   | Naperville, IL | 4 (2 dependents)                         | 19       | 2          | ~$3.4M    |
| 3   | Whitfield-Torres | Brentwood, LA  | 4 (2 dependents, 1 with elevated grants) | 25       | 3          | ~$9.5M    |

---

## Schema changes in this phase (migration 0005)

Both implemented before seed script work begins:

- **`heloc` account type** — added to `account_type` enum after `personal_loan`.
  Frontend: `ACCOUNT_LABELS.heloc = "HELOC"`, `AccountType` union updated.
- **`fire_scenarios.member_id`** — nullable UUID FK → `household_members(id) ON DELETE SET NULL`.
  Passed through `FireScenarioCreate`, `FireScenarioUpdate`, `FireScenarioResponse`.

---

## Schema delta: spec vs. actual implementation

The spec's "Schema quick reference" was written against the design doc; the
implementation diverged in several places. The seed script **must** use the actual
schema below, ignoring the spec's column names where they conflict.

### Members / Users

The spec treats `members` as having `email` and `password_hash`. The actual schema
splits these across two tables:

| Spec                               | Actual                                                |
| ---------------------------------- | ----------------------------------------------------- |
| `members.email`                    | `users.email`                                         |
| `members.password_hash`            | `users.hashed_password` (bcrypt)                      |
| `members.display_name` (encrypted) | `household_members.display_name` (plain `String(80)`) |
| —                                  | `users.member_id` FK → `household_members.id`         |

The seed script must create one `household_members` row + one `users` row per
primary/partner member. Dependents get a `household_members` row but need not have
a `users` row unless they should be able to log in (they cannot in the spec — no
login credentials are listed for Emma, Noah, Sophia, or Ethan).

`display_name` on `household_members` is **not** encrypted in the actual model.
Do not pass it through `encrypt()`.

### Account fields

| Spec                                    | Actual                                                                                                                                                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `accounts.name` (encrypted)             | `accounts.nickname` (plain `String(100)`)                                                                                                                                                                     |
| `accounts.institution` (encrypted)      | `accounts.institution_name_enc` (AES-256-GCM `BYTEA`)                                                                                                                                                         |
| `accounts.last_four`                    | Derived from `accounts.account_number_enc` — store the 4-digit string as `encrypt("1234")` in `account_number_enc`; the API response derives `account_number_last4` by decrypting and taking the last 4 chars |
| `accounts.ownership` (individual/joint) | No `ownership` column — joint is represented by `owner_member_id = NULL`                                                                                                                                      |
| `accounts.member_id`                    | `accounts.owner_member_id`                                                                                                                                                                                    |

### Account type mapping

| Spec value                             | Actual enum value                                      | Notes                                                                          |
| -------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `brokerage`                            | `investment_brokerage`                                 | 529s also use this type                                                        |
| `retirement_ira` (for Roth)            | `retirement_roth_ira`                                  | The spec uses `retirement_ira` for all IRA variants; actual has separate types |
| `retirement_ira` (for traditional/SEP) | `retirement_ira`                                       | Covers traditional IRA and Gabriela's SEP-IRA                                  |
| `loan`                                 | `auto_loan` (cars), `personal_loan` (HELOC pending D1) |                                                                                |

### Transaction fields

| Spec                         | Actual                                                            |
| ---------------------------- | ----------------------------------------------------------------- |
| `merchant_name` (encrypted)  | `payee_raw` (plain `String(255)`) — no encryption                 |
| `memo` (encrypted)           | `memo` (plain `String(500)`) — no encryption                      |
| `is_cleared: bool`           | `is_reviewed: bool` — use this field instead                      |
| `category.type = 'transfer'` | No transfer type; use `is_transfer = True` on the transaction row |

Set `is_reviewed = True` for all transactions dated before June 1, 2026.
Set `is_reviewed = False` for June 2026 transactions.

### Category model

| Spec                                                     | Actual                                                                             |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `categories.type` enum (`income`, `expense`, `transfer`) | `categories.is_income: bool` — set `True` for income slugs, `False` for all others |
| `categories.sort_order`                                  | **Column does not exist** — omit; categories display in insertion order            |

Transfer categories (e.g. `cc_payment`, `mortgage_payment`) get `is_income = False`.

**Spec typo**: The `property_management` row lists its own slug as its parent. The
correct parent is `property_expenses`.

### Real estate properties

| Spec                                      | Actual                                                                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `real_estate_properties.name` (encrypted) | **Column does not exist** — property identity comes from its linked `accounts.nickname`            |
| `real_estate_properties.is_active`        | **Column does not exist** — use the linked account's `is_active`                                   |
| `acquisition_date`                        | `purchase_date`                                                                                    |
| `acquisition_price`                       | `purchase_price`                                                                                   |
| `member_id`                               | **No column** — ownership comes from the linked account's `owner_member_id`                        |
| `property_valuations.source = 'api'`      | Actual enum: `'manual'`, `'api_attom'`, `'api_estated'` — use `'manual'` for all seeded valuations |

For each real estate account, create:

1. An `accounts` row (type `real_estate`, `nickname` = street address short form, `current_balance` = most recent valuation)
2. A `real_estate_properties` row with `account_id` pointing to (1)
3. All `property_valuations` rows with `real_estate_property_id` pointing to (2)

### Account snapshots

The spec calls these "Investment Account Balance Snapshots." The actual table is
`account_snapshots` with columns `account_id`, `snapshot_date`, `balance`,
`contributed_ytd`, `employer_match_ytd`, `memo`, `source`.

Generate one snapshot per calendar month (last calendar day) from 2024-01-31
through 2026-05-31. The June 2026 balance lives in `accounts.current_balance`,
not a snapshot. Set `source = 'manual'` for all generated snapshots.

### FIRE scenarios

| Spec                       | Actual                                                               |
| -------------------------- | -------------------------------------------------------------------- |
| `fire_scenarios.member_id` | **Column does not exist** (pending D2) — omit or use after migration |
| `expected_return_annual`   | `expected_annual_return`                                             |
| `inflation_rate_annual`    | `expected_inflation_rate`                                            |
| `target_annual_spend`      | `target_annual_spend` ✓                                              |
| `target_retirement_age`    | `target_retirement_age` ✓                                            |

The `additional_income_streams` JSON must use `IncomeStreamType` values from
`app/schemas/fire.py`: `salary`, `rental`, `consulting`, `pension`,
`social_security`, `investment`, `other`. The `consulting` type covers Gabriela's
LLC income in H3. All existing spec values map cleanly.

### Debt records

The spec's "Debt Payoff Scenario" section (`strategy`, `extra_monthly_payment`)
describes **UI query parameters**, not persisted rows. The seed script creates
`debts` rows with the loan parameters (`original_balance`, `current_balance`,
`interest_rate`, `minimum_payment`, `loan_term_months`, `origination_date`).
The API calculates avalanche/snowball projections on request.

### Account access grants

| Spec                  | Actual column                                         |
| --------------------- | ----------------------------------------------------- |
| `granted_to` (member) | `grantee_member_id`                                   |
| `granted_by` (member) | `granted_by_user_id` — **user** UUID, not member UUID |
| `account_id`          | `account_id` ✓                                        |
| `owner_member_id`     | The account owner's member UUID                       |

For H2 (Carmen viewing Darius's 401k) and H3 (Sophia viewing 3 joint accounts),
the `granted_by_user_id` must reference the grantor's `users.id`, not their
`household_members.id`.

### Encryption

| Spec                                                | Actual                                    |
| --------------------------------------------------- | ----------------------------------------- |
| `from app.services.encryption import encrypt_field` | `from app.core.encryption import encrypt` |

Encrypted columns in the seed script:

- `accounts.institution_name_enc` — `encrypt(institution_name)`
- `accounts.account_number_enc` — `encrypt(last4_digits)` (store only last 4; service derives display value)
- `real_estate_properties.address_enc` — `encrypt(full_address)`

`accounts.nickname` is **not** encrypted. `household_members.display_name` is
**not** encrypted. Transaction `payee_raw` and `memo` are **not** encrypted.

---

## Seed script architecture

```
backend/
  scripts/
    seed_demo_data.py                  # entry point
    seed_households/
      __init__.py
      shared_categories.py            # category taxonomy, returns {slug: uuid} map
      h1_chen_nakamura.py
      h2_okonkwo_rivera.py
      h3_whitfield_torres.py
```

### Entry point shape

```python
# seed_demo_data.py
import asyncio, argparse, random, time
from decimal import Decimal
from app.db.base import async_session_factory

async def main(household: str) -> None:
    rng = random.Random(42)   # deterministic across runs
    async with async_session_factory() as session:
        async with session.begin():
            if household in ("1", "all"):
                from seed_households.h1_chen_nakamura import seed as seed_h1
                await seed_h1(session, rng)
            if household in ("2", "all"):
                from seed_households.h2_okonkwo_rivera import seed as seed_h2
                await seed_h2(session, rng)
            if household in ("3", "all"):
                from seed_households.h3_whitfield_torres import seed as seed_h3
                await seed_h3(session, rng)
    print_summary()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--household", choices=["1", "2", "3", "all"], default="1")
    asyncio.run(main(parser.parse_args().household))
```

### Transaction generator

```python
def generate_month_transactions(
    month_start: date,
    patterns: list[TransactionPattern],
    account_map: dict[str, uuid.UUID],
    category_map: dict[str, uuid.UUID],
    property_map: dict[str, uuid.UUID],
    rng: random.Random,
) -> list[dict]:
    ...
```

Rules:

1. Fixed amounts: exact; use specified date.
2. Variable categories: sample total in range, split into N transactions
   where N is sampled from the frequency range; dates spread across weekdays
   avoiding Sundays for grocery shops, preferring Fridays for restaurants.
3. `is_reviewed = True` for all dates before 2026-06-01.
4. Transfer transactions create two rows (debit source, credit destination)
   both with `is_transfer = True` and identical `memo`.
5. Apply ±10% jitter to variable amounts using `rng`.
6. `source = 'manual'` on all transactions.

### Balance snapshot formula

```python
def compute_snapshots(
    start_balance: Decimal,
    monthly_contributions: dict[date, Decimal],
    annual_return: float = 0.09,
    dips: dict[date, float] | None = None,   # e.g. {date(2024,10,31): -0.03}
) -> list[tuple[date, Decimal]]:
    balance = start_balance
    for month_end in month_end_range(date(2024,1,31), date(2026,5,31)):
        monthly_growth = Decimal(str(annual_return / 12))
        balance = balance * (1 + monthly_growth)
        balance += monthly_contributions.get(month_end, Decimal(0))
        if dips and month_end in dips:
            balance *= Decimal(str(1 + dips[month_end]))
        yield month_end, balance.quantize(Decimal("0.0001"))
```

---

## Feature surfaces exercised per household

| Feature                                 | H1         | H2                | H3                      |
| --------------------------------------- | ---------- | ----------------- | ----------------------- |
| Two-member RBAC (primary + partner)     | ✓          | ✓                 | ✓                       |
| Dependent read-only members             | —          | ✓ (Emma, Noah)    | ✓ (Ethan)               |
| Elevated access grants for dependent    | —          | —                 | ✓ (Sophia)              |
| Budget vs. actuals                      | ✓          | ✓                 | ✓                       |
| Budget history (effective_from)         | ✓          | ✓                 | ✓                       |
| Single primary residence                | ✓          | ✓                 | ✓                       |
| Long-term rental property               | —          | ✓                 | ✓                       |
| Vacation / STR rental property          | —          | —                 | ✓                       |
| 529 college savings (as brokerage)      | —          | ✓                 | ✓                       |
| HSA                                     | ✓          | ✓                 | ✓                       |
| FIRE scenario                           | ✓ (1)      | ✓ (2)             | ✓ (2)                   |
| Debt payoff (avalanche)                 | ✓ (1 loan) | ✓ (2 loans)       | ✓ (1 loan)              |
| Seasonal spending patterns              | ✓          | ✓                 | ✓                       |
| Credit card payments as transfers       | ✓          | ✓                 | ✓                       |
| Rental income + P&L                     | —          | ✓                 | ✓                       |
| STR (Airbnb) income + property mgmt fee | —          | —                 | ✓                       |
| Property tax as recurring expense       | —          | ✓                 | ✓                       |
| HELOC                                   | —          | —                 | ✓ (pending D1)          |
| SEP-IRA                                 | —          | —                 | ✓ (as `retirement_ira`) |
| Profit-sharing / partner distribution   | —          | ✓                 | ✓                       |
| Year-end bonus                          | —          | ✓                 | —                       |
| Annual lump-sum contributions           | —          | ✓ (backdoor Roth) | ✓ (SEP + 401k PS)       |
| Property manager fee (% of income)      | —          | —                 | ✓                       |

---

## Execution

```bash
# Standard: run via docker-compose exec (PostgreSQL is only accessible inside
# the Docker network — hostname "db" does not resolve outside it):
docker-compose exec backend python scripts/seed_demo_data.py --household all

# Single-household demo instance:
docker-compose exec backend python scripts/seed_demo_data.py --household 1

# Local dev only (requires a local PostgreSQL and DATABASE_URL pointing to
# localhost instead of "db"):
uv run --directory backend python scripts/seed_demo_data.py --household all
```

The script prints a summary table with computed net worth per household as a
sanity check after all inserts complete. Do not insert rows into `audit_log`
from the seed script (the app role has only SELECT + INSERT on that table;
seeded data is bootstrap, not an audited event stream).

---

## Notes on `--household all`

The production architecture is single-household-per-installation. `--household all`
is explicitly for demo/test environments. With all three households seeded, users
must log in with the correct household's credentials to see that household's data:

| Household        | Login email                     | Password     |
| ---------------- | ------------------------------- | ------------ |
| Chen-Nakamura    | wei@chen-nakamura.local         | HearthDemo1! |
| Chen-Nakamura    | priya@chen-nakamura.local       | HearthDemo1! |
| Okonkwo-Rivera   | darius@okonkwo-rivera.local     | HearthDemo1! |
| Okonkwo-Rivera   | carmen@okonkwo-rivera.local     | HearthDemo1! |
| Whitfield-Torres | ben@whitfield-torres.local      | HearthDemo1! |
| Whitfield-Torres | gabriela@whitfield-torres.local | HearthDemo1! |

The `VisibilityContext` resolved from the JWT ensures each user sees only their
own household's data regardless of how many households are in the DB.
