# Phase 11 — Demo Households H4 (Park-Cole) and H5 (Langford)

**Status:** Design
**Date:** 2026-06-21
**Scope:** Add two new demo seed households, extend the shared category taxonomy, fix the seed guard to allow additive seeding, and make DATE_END env-configurable. No frontend changes, no Alembic migrations.

---

## 1. Context

Phases 1–10 established HearthLedger's core feature surface. The demo seed script (`backend/scripts/seed_demo_data.py`) currently generates three households (H1 Chen-Nakamura, H2 Okonkwo-Rivera, H3 Whitfield-Torres) that collectively exercise: net worth tracking, RBAC, property P&L, 529 accounts, HELOC, SEP-IRA, multi-scenario FIRE, avalanche/snowball debt payoff, and STR rental income.

Phase 11 adds H4 Park-Cole and H5 Langford, which introduce household archetypes and income types not yet covered:

|                | H4 Park-Cole                                                 | H5 Langford                                                               |
| -------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| Profile        | Late 20s Nashville renters, early debt payoff                | Sarasota retirees, RMD + Social Security                                  |
| Net worth      | ~$154,500                                                    | ~$12,856,700                                                              |
| Novel concepts | Rent-only housing, debt cascade (3 loans), aspirational FIRE | RMD income, SS income, pension, Medicare IRMAA, ACA premium, LLC checking |

Both households are specified in `docs/hearthledger-demo-data-spec-addendum.md`. The implementation spec for H1–H3 (`docs/hearthledger-demo-data-spec-revised.md`) defines the seed framework that H4/H5 extend.

---

## 2. Gaps Analysis

### 2.1 Category taxonomy gaps

`backend/scripts/seed_households/shared_categories.py` is missing these slugs, which H4 and H5 require:

**Income — new retirement/government income types:**

| Slug                     | Name                          | Parent              | Notes                             |
| ------------------------ | ----------------------------- | ------------------- | --------------------------------- |
| `social_security_income` | Social Security               | `other_income`      | H5 — SSA monthly deposits for Bob |
| `pension_income`         | Pension Income                | `other_income`      | H5 — County pension payments      |
| `rmd_distribution`       | Required Minimum Distribution | `investment_income` | H5 — Bob's annual RMD from IRA    |

**Expense — renter housing:**

| Slug                | Name              | Parent    | Notes                      |
| ------------------- | ----------------- | --------- | -------------------------- |
| `rent`              | Rent              | `housing` | H4 — monthly rent payments |
| `renters_insurance` | Renters Insurance | `housing` | H4 — annual renters policy |

**Expense — retirement healthcare:**

| Slug                 | Name                    | Parent       | Notes                                |
| -------------------- | ----------------------- | ------------ | ------------------------------------ |
| `medicare_part_b`    | Medicare Part B         | `healthcare` | H5 — Bob's Part B premium + IRMAA    |
| `medicare_part_d`    | Medicare Part D         | `healthcare` | H5 — Bob's prescription drug premium |
| `medigap_supplement` | Medigap Supplement      | `healthcare` | H5 — Bob's Medigap Plan G            |
| `aca_premium`        | ACA Marketplace Premium | `healthcare` | H5 — Maggie's marketplace coverage   |

All 9 are added to the shared `_DEFS` list. Since categories are created per-household, this addition does not affect existing H1–H3 data.

### 2.2 Account type enum — no changes needed

The actual SQLAlchemy `ACCOUNT_TYPES` enum (in `app/db/models/account.py`) is richer than the addendum's spec shorthand. H4/H5 seed files must use the actual enum values, consistent with H1–H3:

| Addendum spec shorthand                   | Actual enum value to use                                                |
| ----------------------------------------- | ----------------------------------------------------------------------- |
| `loan` (auto)                             | `auto_loan`                                                             |
| `loan` (student)                          | `student_loan`                                                          |
| `brokerage`                               | `investment_brokerage`                                                  |
| `retirement_ira` (Roth)                   | `retirement_roth_ira`                                                   |
| `retirement_ira` (Traditional / Rollover) | `retirement_ira`                                                        |
| `retirement_401k` (Roth or Trad 401k)     | `retirement_401k` (no separate Roth 401k type; distinction by nickname) |

### 2.3 Debt cascade — already supported

`app/services/debt_projector.py:project_payoff()` already implements the cascade at line 124: when any debt reaches zero, its minimum payment is added to `available_extra` and applied to the next target. For H4, passing all three debts (Honda Accord, Zoe Student Loan, Marcus Student Loan) to `project_payoff(strategy='avalanche', extra_monthly_payment=500)` will automatically produce the cascade with no engine changes.

The seed script creates three `Debt` table rows for H4 — the payoff projection is computed live by the API, not stored.

### 2.4 RMD income — data-only, no engine changes

H5's RMD is modeled as periodic income transactions tagged `rmd_distribution`. The FIRE scenario's `additional_income_streams` JSONB already supports arbitrary labeled income types. No backend calculation of RMD factors is needed in Phase 11 — the seed script inserts the pre-computed annual distribution amounts directly as transactions.

Bob Langford was born February 18, 1952. In 2024 he is 72; he turns 73 in February 2025. Under SECURE 2.0, his first RMD year is 2025. The 2025 RMD uses Uniform Lifetime Table divisor **26.5** (age 73): $3,699,000 ÷ 26.5 = **$139,585**. The 2026 RMD uses divisor **25.5** (age 74): $3,726,000 ÷ 25.5 = **$146,118**.

### 2.5 Real estate without a linked mortgage — verify graceful display

H5's Sarasota primary residence was a cash purchase (no mortgage). The `linked_mortgage_account_id` on `real_estate_properties` will be `null`. The Assets page equity display must handle `null` here without crashing. This is a verification item, and the existing `Assets.test.tsx` does not cover the null mortgage case — add a test (see checklist).

### 2.6 LLC checking account — no model changes

Maggie Langford's consulting LLC checking maps to `account_type = 'checking'`, `ownership = 'individual'`, `owner_member_id = Maggie`. No new model needed.

### 2.7 Seed guard and DATE_END (Approach B additions)

`seed_demo_data.py` currently calls `_has_existing_households()` which exits if **any** household exists. This blocks additive seeding of H4/H5 to an environment that already has H1–H3. Fix: change the guard to a per-household `_household_exists(session, name)` check.

`_util.py` has `DATE_END = date(2026, 6, 21)` hardcoded. Make it read from `SEED_DATE_END` env var with fallback to the hardcoded date so seeds remain usable post-2026-06-21.

---

## 3. Implementation Plan

### Phase 11.A — Extend shared category taxonomy

**File:** `backend/scripts/seed_households/shared_categories.py`

Add 9 entries to `_DEFS` in the appropriate sections:

```python
# In income section, after ("misc_income", ...):
("social_security_income", "Social Security",                  "other_income",     True),
("pension_income",         "Pension Income",                   "other_income",     True),

# In investment_income section, after ("capital_gains", ...):
("rmd_distribution",       "Required Minimum Distribution",    "investment_income", True),

# In housing section, after ("cleaning_services", ...):
("rent",                   "Rent",                             "housing",          False),
("renters_insurance",      "Renters Insurance",                "housing",          False),

# In healthcare section, after ("therapy", ...):
("medicare_part_b",        "Medicare Part B",                  "healthcare",       False),
("medicare_part_d",        "Medicare Part D",                  "healthcare",       False),
("medigap_supplement",     "Medigap Supplement",               "healthcare",       False),
("aca_premium",            "ACA Marketplace Premium",          "healthcare",       False),
```

### Phase 11.B — H4 Park-Cole seed module

**New file:** `backend/scripts/seed_households/h4_park_cole.py`

**Members:**

- Zoe Park (primary, age 27)
- Marcus Cole (partner, age 28)

**Accounts (13 total):**

| #   | Nickname               | Type                   | Owner  | Institution    | Last4 | Balance     |
| --- | ---------------------- | ---------------------- | ------ | -------------- | ----- | ----------- |
| 1   | Joint Checking         | `checking`             | joint  | Ally Bank      | 4492  | $9,400.00   |
| 2   | Emergency Fund         | `savings`              | joint  | Ally Bank      | 5513  | $35,000.00  |
| 3   | House Fund             | `investment_brokerage` | joint  | Fidelity       | 6624  | $88,400.00  |
| 4   | Roth 401(k)            | `retirement_401k`      | Zoe    | Guideline      | 7735  | $22,400.00  |
| 5   | 401(k)                 | `retirement_401k`      | Marcus | Fidelity (HCA) | 8846  | $46,800.00  |
| 6   | Roth IRA               | `retirement_roth_ira`  | Zoe    | Fidelity       | 9957  | $12,200.00  |
| 7   | Roth IRA               | `retirement_roth_ira`  | Marcus | Vanguard       | 1068  | $9,400.00   |
| 8   | HSA                    | `hsa`                  | Zoe    | HealthEquity   | 2179  | $5,200.00   |
| 9   | Freedom Unlimited      | `credit_card`          | joint  | Chase          | 3280  | -$2,400.00  |
| 10  | Apple Card             | `credit_card`          | Zoe    | Goldman Sachs  | 4381  | -$1,100.00  |
| 11  | Federal Student Loan   | `student_loan`         | Zoe    | MOHELA         | 5492  | -$34,000.00 |
| 12  | Federal Student Loan   | `student_loan`         | Marcus | MOHELA         | 6503  | -$22,000.00 |
| 13  | Honda Accord Auto Loan | `auto_loan`            | Marcus | Tennessee CU   | 7614  | -$14,800.00 |

No real estate accounts — this household rents.

**Net worth sanity check:**
Assets: 9,400 + 35,000 + 88,400 + 22,400 + 46,800 + 12,200 + 9,400 + 5,200 = **228,800**
Liabilities: 2,400 + 1,100 + 34,000 + 22,000 + 14,800 = **74,300**
**Net worth: $154,500** ✓

**Income pattern:**

- Zoe: biweekly (7th and 21st), $2,210/check, "DataOps Inc. Payroll" → Joint Checking
- Marcus: biweekly (1st and 15th), $2,870/check, "HCA Healthcare Payroll" → Joint Checking
- Extra 3rd paycheck months: Zoe (March, August, November 2024); Marcus (January, June, November 2024)
- Annual federal tax refund April: $1,650, "IRS TREAS 310", category `tax_refund`

**Key expense categories used:**

- `rent` — $1,875/mo to "4th Ave Partners" (East Nashville apartment)
- `renters_insurance` — $22/mo, State Farm
- `loan_payment` — auto + student loan payments (see debt section)
- Standard household spend split between Chase Freedom Unlimited (Account #9) and Apple Card (Account #10)

**Debt payoff scenario (3 debts, avalanche by APR):**

| Loan                | Account | Member | Original | Current | APR   | Min Monthly | Start   |
| ------------------- | ------- | ------ | -------- | ------- | ----- | ----------- | ------- |
| Honda Accord Auto   | #13     | Marcus | $18,500  | $14,800 | 6.90% | $312        | 2022-03 |
| Zoe Student Loan    | #11     | Zoe    | $42,000  | $34,000 | 5.50% | $275        | 2021-08 |
| Marcus Student Loan | #12     | Marcus | $28,000  | $22,000 | 4.80% | $182        | 2019-06 |

Avalanche order (highest APR first): Honda Accord → Zoe Student → Marcus Student.

Monthly payment schedule during Honda period (Jan 2024–Aug 2025):

- Honda Accord: $812/mo (min $312 + extra $500)
- Zoe Student: $675/mo (min $275 + extra $400)
- Marcus Student: $182/mo (minimum only)

Payoff event ~August/September 2025: Honda Accord reaches $0. Starting October 2025: Zoe Student payment increases to $775/mo (min $275 + cascaded $500 extra). Honda account sets `is_active = false`, $0 balance. Marcus Student remains at $182/mo (his loan payoff cascade occurs after Zoe's is cleared, outside the 30-month data window).

The seed creates three `Debt` rows; the API's `project_payoff()` engine computes the live projection.

**FIRE scenario:** "Financial Independence by 45"

- `member_id`: Zoe
- `target_annual_spend = 120_000`
- `expected_annual_return = 0.075`
- `inflation_rate_annual = 0.030`
- `target_retirement_age = 45`
- Income streams: Zoe salary (DataOps, $78K, 4% growth, 2024–2044), Marcus salary (HCA, $88K, 3.5% growth, 2024–2042), Zoe SS at 67 ($34K/yr, 2064+), Marcus SS at 67 ($38K/yr, 2064+)
- Intentionally aspirational: at current savings rates, the projection likely misses 45 — demonstrates FIRE gap visualization

**Investment account snapshots:** Monthly Jan 2024–May 2026.

| Account              | Jan 2024 | Monthly Contribution          | Growth Rate |
| -------------------- | -------- | ----------------------------- | ----------- |
| Zoe Roth 401(k) (#4) | $14,200  | $390/mo                       | 8.5%        |
| Marcus 401(k) (#5)   | $32,400  | $440/mo + $293 employer match | 8.5%        |
| Zoe Roth IRA (#6)    | $7,800   | $583/mo Jan–Oct, $0 Nov–Dec   | 8.5%        |
| Marcus Roth IRA (#7) | $5,200   | $583/mo Jan–Oct, $0 Nov–Dec   | 8.5%        |
| Zoe HSA (#8)         | $2,200   | $358/mo                       | 8.5%        |
| House Fund (#3)      | $42,000  | $2,000/mo                     | 6.5%        |

Growth formula: `balance[m] = balance[m-1] × (1 + rate/12) + contribution[m]`. Apply a -3.5% drawdown to all investment accounts in October 2024. House Fund uses 6.5% (shorter horizon, 60/40 allocation) with formula `balance[m] = balance[m-1] × (1 + 0.065/12) + 2000`.

### Phase 11.C — H5 Langford seed module

**New file:** `backend/scripts/seed_households/h5_langford.py`

**Members:**

- Robert ("Bob") Langford (primary, born 1952-02-18 — age 72 in Jan 2024, age 73 in Feb 2025, age 74 in Feb 2026)
- Margaret ("Maggie") Langford (partner, age 63 in 2026)

**Accounts (15 total):**

| #   | Nickname                   | Type                   | Owner  | Institution         | Last4 | Balance       |
| --- | -------------------------- | ---------------------- | ------ | ------------------- | ----- | ------------- |
| 1   | Wealth Management Checking | `checking`             | joint  | Truist Bank Private | 8847  | $62,000.00    |
| 2   | Premium Savings            | `savings`              | joint  | Truist Bank Private | 9958  | $128,000.00   |
| 3   | Money Market (SWVXX)       | `savings`              | joint  | Schwab              | 1069  | $265,000.00   |
| 4   | Consulting LLC Checking    | `checking`             | Maggie | Regions Bank        | 2170  | $38,500.00    |
| 5   | Bob Rollover IRA           | `retirement_ira`       | Bob    | Schwab              | 3281  | $3,850,000.00 |
| 6   | Maggie Rollover IRA        | `retirement_ira`       | Maggie | Schwab              | 4392  | $720,000.00   |
| 7   | Bob Roth IRA               | `retirement_roth_ira`  | Bob    | Fidelity            | 5403  | $88,000.00    |
| 8   | Maggie Roth IRA            | `retirement_roth_ira`  | Maggie | Vanguard            | 6514  | $110,000.00   |
| 9   | Joint Taxable Brokerage    | `investment_brokerage` | joint  | Schwab              | 7625  | $3,280,000.00 |
| 10  | Bob Individual Brokerage   | `investment_brokerage` | Bob    | Fidelity            | 8736  | $720,000.00   |
| 11  | Centurion Card             | `credit_card`          | Bob    | American Express    | 9847  | -$6,200.00    |
| 12  | Sapphire Reserve           | `credit_card`          | joint  | Chase               | 1058  | -$1,600.00    |
| 13  | Highlands NC Mortgage      | `mortgage`             | joint  | Bank of America     | 2169  | -$342,000.00  |
| 14  | Sarasota Primary Home      | `real_estate`          | joint  | —                   | —     | $2,850,000.00 |
| 15  | Highlands NC Vacation Home | `real_estate`          | joint  | —                   | —     | $1,095,000.00 |

Note: Account #6 (Maggie Rollover IRA) holds Maggie's former SEP-IRA, rolled over in 2023 when she left corporate employment. She still makes annual SEP contributions that Schwab credits directly — add lump-sum adjustment to January snapshots ($58K in Jan 2024, $61K in Jan 2025).

**Net worth sanity check:**
Assets: 62,000 + 128,000 + 265,000 + 38,500 + 3,850,000 + 720,000 + 88,000 + 110,000 + 3,280,000 + 720,000 + 2,850,000 + 1,095,000 = **13,206,500**
Liabilities: 6,200 + 1,600 + 342,000 = **349,800**
**Net worth: $12,856,700** ✓

**Real estate:**

- Sarasota Primary (Account #14): cash purchase, `linked_mortgage_account_id = null`, `property_type = 'primary_residence'`, acquisition_date 2022-03-18, acquisition_price $2,100,000. 6 valuations: $2,580K (Jan 2024), $2,650K (Jul 2024), $2,720K (Jan 2025), $2,780K (Jul 2025), $2,830K (Jan 2026), $2,850K (Jun 2026).
- Highlands Vacation (Account #15): linked to mortgage Account #13, `property_type = 'vacation'`, acquisition_date 2019-06-04, acquisition_price $720,000. Monthly P&I: $1,632 (30yr at 3.25%). 6 valuations: $985K (Jan 2024), $1,010K (Jul 2024), $1,042K (Jan 2025), $1,068K (Jul 2025), $1,085K (Jan 2026), $1,095K (Jun 2026).

**Income pattern (retirement-phase, all to Account #1 unless noted):**

| Source                 | Deposit Date                | Amount                          | Category                 | Merchant                        | Notes                                                 |
| ---------------------- | --------------------------- | ------------------------------- | ------------------------ | ------------------------------- | ----------------------------------------------------- |
| Social Security (Bob)  | 3rd Wednesday               | $4,886/mo                       | `social_security_income` | "US Treasury Social Security"   | Net of Medicare deductions; gross SS $5,417/mo        |
| Meridian Pension (Bob) | 1st of month                | $4,000/mo                       | `pension_income`         | "Meridian Packaging Pension"    | Fixed $48K/yr                                         |
| Bob IRA RMD (2025+)    | Quarterly schedule          | $34,896–$36,530                 | `rmd_distribution`       | "Schwab IRA Distribution — RMD" | $0 in 2024; quarterly from Q1 2025                    |
| Maggie Consulting      | 15th of month               | ~$3,200 avg                     | `consulting_fees`        | "Langford HR Consulting LLC"    | Transfer from LLC Checking (Account #4) to Account #1 |
| Dividends — Joint      | Last day of Mar/Jun/Sep/Dec | $18,500/$19,200/$20,100/$21,000 | `dividends`              | "Schwab Brokerage Dividend"     | Quarterly                                             |
| Dividends — Bob        | Last day of Mar/Jun/Sep/Dec | $4,200 each                     | `dividends`              | "Fidelity Brokerage Dividend"   | To Account #1                                         |

**RMD quarterly schedule:**

2025 total: $139,585 (basis: $3,699,000 Dec 31 2024 ÷ 26.5, age 73)

- Q1 2025 (March 31): $34,896
- Q2 2025 (June 30): $34,896
- Q3 2025 (Sept 30): $34,896
- Q4 2025 (Dec 15): $34,897

2026 total (partial): basis $3,726,000 Dec 31 2025 ÷ 25.5 (age 74) = $146,118/yr

- Q1 2026 (March 31): $36,530
- Q2 2026 (June 30): $36,530

**Key expense categories used:**

- `medicare_part_b` — Bob's Part B + IRMAA Tier 1 (~$280/mo in 2024–2025, $284.10/mo in 2026)
- `medicare_part_d` — Bob's Part D (~$48/mo in 2024–2025, $49/mo in 2026)
- `medigap_supplement` — Bob's Medigap Plan G ($192/mo 2024–2025, $198/mo 2026)
- `aca_premium` — Maggie's ACA (2024: $1,165/mo → 2025: $1,245/mo → 2026: $1,310/mo)
- `mortgage_payment` — Highlands NC $1,632/mo to Account #13

ACA budget revisions: add `aca_premium` budget revision effective 2025-01-01 at $1,245, and another effective 2026-01-01 at $1,310.

**Investment account snapshots:** Monthly Jan 2024–May 2026.

| Account                        | Jan 2024   | Monthly Contribution       | Growth Rate | Notes                                                          |
| ------------------------------ | ---------- | -------------------------- | ----------- | -------------------------------------------------------------- |
| Bob Rollover IRA (#5)          | $3,450,000 | $0                         | 7%          | RMD withdrawals reduce balance quarterly from 2025             |
| Maggie Rollover IRA (#6)       | $602,000   | $0                         | 7%          | Add $58K lump Jan 2024; $61K lump Jan 2025 (SEP contributions) |
| Bob Roth IRA (#7)              | $72,000    | $583/mo Jan–Oct (backdoor) | 7%          | Exempt from RMDs                                               |
| Maggie Roth IRA (#8)           | $88,000    | $583/mo Jan–Oct (backdoor) | 7%          | Exempt from RMDs                                               |
| Joint Brokerage (#9)           | $2,780,000 | $2,000/mo                  | 6.5%        | -4% dip Oct 2024; -2.5% dip Apr 2025                           |
| Bob Individual Brokerage (#10) | $612,000   | $1,000/mo                  | 6.5%        | Same dips                                                      |

**FIRE scenarios:**

_Scenario A — "30-Year Portfolio Sustainability"_

- `member_id`: Bob; `target_retirement_age = 95`
- `target_annual_spend = 280_000`; `expected_annual_return = 0.055`; `inflation_rate_annual = 0.030`
- Income streams: Bob SS ($65,004/yr, 2020+, 2.5% COLA), Bob pension ($48,000/yr fixed, 2020–2045), Maggie consulting ($48,000/yr, 2024–2029, -5%/yr growth), Maggie former-employer pension ($28,800/yr, 2027–2055), Maggie SS at FRA 67 ($42,000/yr, 2029+), joint brokerage dividends ($78,000/yr, 2.0% growth)

_Scenario B — "Longevity Stress Test (to Age 100)"_

- `member_id`: Bob; `target_retirement_age = 100`
- `target_annual_spend = 320_000`; `expected_annual_return = 0.045`; `inflation_rate_annual = 0.035`
- Same income streams as A but SS COLA 1.5%, pension end years shortened (2042 and 2050), consulting excluded

**Debt scenario:**

- Highlands NC Mortgage (#13): strategy `avalanche`, extra_monthly_payment $0 (rate arbitrage — 3.25% < expected portfolio return)
- Mortgage detail: 30yr fixed 3.25%, originated 2019-06-04 (7 years in), original loan $375,000, current balance $342,000, monthly P&I $1,632

### Phase 11.D — Seed script entry point

**File:** `backend/scripts/seed_demo_data.py`

- Replace `_has_existing_households()` guard with per-household `_household_exists(session, household_name)` check
- Add `'4': seed_h4_park_cole` and `'5': seed_h5_langford` to dispatch table
- Update argparse `choices` to include `"4"`, `"5"`, `"all"`
- Update `--household all` to include H4 and H5 in sequence
- Update summary table output to include H4/H5 rows

### Phase 11.E — Utility: DATE_END env override

**File:** `backend/scripts/seed_households/_util.py`

Change `DATE_END`:

```python
import os
from datetime import date
_DATE_END_ENV = os.getenv("SEED_DATE_END")
DATE_END: date = (
    date.fromisoformat(_DATE_END_ENV) if _DATE_END_ENV
    else date(2026, 6, 21)
)
```

Document `SEED_DATE_END` in `.env.example` as a commented seed-only variable.

### Phase 11.F — Verification

Before shipping, run:

```bash
# Single-household test (on fresh DB, or with additive guard fix in place)
python backend/scripts/seed_demo_data.py --household 4
python backend/scripts/seed_demo_data.py --household 5

# Full suite
python backend/scripts/seed_demo_data.py --household all

# Verify net worth sanity
# H4 expected: ~$154,500 (±$1K)
# H5 expected: ~$12,856,700 (±$1K)
```

Manual spot-checks:

- H4: confirm `rent` category transactions appear; confirm Assets page shows empty state (no properties); confirm Honda loan account shows `is_active = false` after Sept 2025; confirm Zoe Student loan payment increases to $775/mo in Oct 2025
- H5: confirm `social_security_income`, `pension_income`, `rmd_distribution` transactions appear in cash flow; confirm Sarasota property (Account #14) shows equity without a mortgage balance displayed; confirm ACA premium uses $1,165 in 2024, $1,245 in 2025, $1,310 in 2026; confirm RMD transactions begin in Q1 2025 (not 2024)

---

## 4. Design Decisions

**New categories go into `shared_categories.py` (not household-specific)**
All five demo households are US households and could plausibly have Social Security, pensions, or Medicare. Putting these in the shared taxonomy means any real user adding their own data can use these categories without patching the system categories.

**RMD modeled as income transactions, not a calculated field**
The seed inserts RMD amounts as pre-computed transactions. The backend does not need a Uniform Lifetime Table lookup. If a future phase adds an RMD planning calculator, it can read `rmd_distribution`-tagged transactions as its reference data.

**Medicare IRMAA modeled as a higher `medicare_part_b` amount**
IRMAA is a surcharge on top of the standard Part B premium, not a separate line. The seed rolls the surcharge into the `medicare_part_b` transaction amount. This keeps the category model simple.

**Bob's SS transaction uses the net deposit amount**
Bob's SS gross is $5,417/mo; Medicare premiums are auto-deducted by SSA before deposit. The seed records the net deposit ($4,886/mo) as `social_security_income` and also records the Medicare premiums as separate expense transactions for healthcare tracking. This matches real bank statement behavior and avoids fabricating a gross-then-deduction flow that doesn't exist in the actual checking account.

**Debt cascade: no stored "cascade config"**
The cascade is a projection-time behavior, not stored state. The three `Debt` rows for H4 are seeded as individual records. The API's `project_payoff()` produces the cascade automatically. The seed's historical transactions model the actual payment amounts per the spec (Honda pays off Aug/Sept 2025; Zoe's payment increases Oct 2025).

**H4 Roth 401(k) uses `retirement_401k` type**
The account model doesn't distinguish traditional vs. Roth 401(k) at the type level — both use `retirement_401k`. The distinction is communicated through the nickname ("Roth 401(k)" vs. "401(k)"). This is a known limitation of the current data model.

**Additive seeding via per-household guard**
Replacing the global `_has_existing_households()` guard with a per-household name check allows running `--household 4` on a database that already has H1–H3 seeded, without data loss.

---

## 5. Out of Scope for Phase 11

- Frontend UI changes for retirement income display (existing category display handles new slugs without changes)
- RMD calculation engine / Uniform Lifetime Table integration
- Medicare IRMAA income-threshold calculation
- "Retirement phase" FIRE mode that starts from current portfolio drawdown
- Snowball/avalanche toggle in the frontend debt view (API already supports both strategies)
- Social Security benefit estimator / break-even analysis
- HSA investment growth modeling for retirees

---

## 6. File Manifest

| File                                                   | Change                                                 |
| ------------------------------------------------------ | ------------------------------------------------------ |
| `backend/scripts/seed_households/shared_categories.py` | Add 9 category entries                                 |
| `backend/scripts/seed_households/h4_park_cole.py`      | New                                                    |
| `backend/scripts/seed_households/h5_langford.py`       | New                                                    |
| `backend/scripts/seed_demo_data.py`                    | Add H4/H5 to dispatch + argparse + per-household guard |
| `backend/scripts/seed_households/_util.py`             | Make DATE_END env-configurable                         |
| `.env.example`                                         | Document SEED_DATE_END (commented, seed-only)          |

No Alembic migrations, no new API endpoints, no frontend changes.

---

## 7. Design Review Checklist

- [ ] No raw account queries outside `AccountRepository.get_visible()`
- [ ] All seed inserts go through existing service methods or direct ORM (seed is not audited per spec)
- [ ] No encrypted field values in audit log entries (seed bypasses audit log per rule in spec)
- [ ] `rent`, `renters_insurance`, and Medicare categories don't create duplicate slugs with existing taxonomy
- [ ] H5 Sarasota primary home (`linked_mortgage_account_id = null`) shows equity correctly in Assets page without crash (add test: `propertiesApi.getEquity` mock with `mortgage_balance_visible: false`)
- [ ] H4 Assets page shows empty state without errors (no real estate accounts)
- [ ] Seed summary output matches expected net worth targets (±$1K): H4 = $154,500, H5 = $12,856,700
- [ ] `--household all` runs cleanly end-to-end without FK or enum errors
- [ ] `--household 4` and `--household 5` both work on a DB that already has H1–H3 (per-household guard check)
- [ ] H4 Honda Accord loan account shows `is_active = false` with $0 balance from October 2025 onward
- [ ] H5 RMD transactions start in Q1 2025 — zero RMD transactions in 2024
- [ ] H5 ACA premium uses $1,165 for 2024, $1,245 for 2025, $1,310 for 2026
