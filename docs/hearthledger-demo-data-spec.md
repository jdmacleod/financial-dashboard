# HearthLedger — Demo Dataset Specification
## Planning Artifact for Claude Code Seed Script Generation

**Date prepared:** June 20, 2026
**Target file:** `backend/scripts/seed_demo_data.py`
**Transaction date range:** January 1, 2024 – June 20, 2026 (≈ 30 months)
**Reference spec:** `~/Documents/hearthledger-spec/` (read `CLAUDE.md` and `docs/data-model.md` before implementing)

---

## 1. Purpose

This document specifies three fictitious US households to populate HearthLedger with realistic demo data. The households are ordered by financial complexity — from a straightforward dual-income couple with no dependents (~$900K net worth) through a multi-generation family with a rental property (~$3.8M net worth) to a high-income Los Angeles household with three properties and a complex FIRE picture (~$9.5M net worth).

The goal is a seed dataset that exercises every major feature surface: net worth tracking with property valuations, cash flow reporting, budget vs. actuals, property-level P&L, FIRE scenario modeling, debt payoff projections, RBAC roles, and the audit log. Each household is calibrated against Federal Reserve 2022 Survey of Consumer Finances benchmarks, 2024-2025 Southern California and national housing data, and 2025 federal / state tax brackets.

---

## 2. Seed Script Approach

### File layout

```
backend/
  scripts/
    seed_demo_data.py          # Entry point — accepts --household 1|2|3|all
    seed_households/
      __init__.py
      shared_categories.py     # Category taxonomy (shared across all households)
      h1_chen_nakamura.py      # Household 1 data definitions
      h2_okonkwo_rivera.py     # Household 2 data definitions
      h3_whitfield_torres.py   # Household 3 data definitions
```

### Execution

```bash
# Generate all three (for a multi-household demo/test instance)
python backend/scripts/seed_demo_data.py --household all

# Generate a single household (for single-household production demo)
python backend/scripts/seed_demo_data.py --household 1
```

The `--household all` flag acknowledges that the production architecture is single-household-per-installation; this mode is explicitly for demo/test environments only.

### Key technical requirements

- Use `asyncio.run()` wrapping an async main function that accepts a `get_db()` session from `app.db.session`.
- Import `encrypt_field` from `app.services.encryption`. **Every** field marked encrypted in the schema must be encrypted before insert. Never write plaintext PII into the DB directly.
- Use `uuid.uuid4()` for all primary keys. Generate UUIDs in Python, not relying on `gen_random_uuid()`, so keys are available as FK references during the same script run.
- Hash passwords with `passlib.context.CryptContext(schemes=["bcrypt"])`. Default demo password for all members: `HearthDemo1!`
- All monetary values are `Decimal` with 4 decimal places (e.g., `Decimal("1234.5600")`). Use Python's `decimal.Decimal`, not float.
- All timestamps use `datetime.utcnow()` for `created_at` fields; all dates use `datetime.date`.
- Transactions are generated programmatically from the monthly patterns defined in each household module. The generator should add ±5–15% random jitter to variable-expense amounts to make them feel realistic. Use a seeded RNG (`random.seed(42)`) so output is deterministic across runs.
- Do NOT insert rows into `audit_log` from the seed script. The audit log is append-only and enforced at the DB permission level; seeded data is bootstrap data, not audited events.
- After seeding, print a summary table of each household's computed net worth (total assets minus total liabilities) as a sanity check.

### Schema quick reference

Verify all enum values against the actual SQLAlchemy `Enum` definitions in `app/models/` before using them. The values below are based on the design spec and may have been adjusted during implementation.

| Table | Key enum column | Expected values |
|---|---|---|
| `members` | `role` | `primary`, `partner`, `dependent` |
| `accounts` | `account_type` | `checking`, `savings`, `credit_card`, `brokerage`, `retirement_401k`, `retirement_ira`, `pension`, `hsa`, `real_estate`, `mortgage`, `loan`, `other` |
| `accounts` | `ownership` | `individual`, `joint` |
| `transactions` | (no enum) | `is_transfer BOOL`, `is_cleared BOOL` |
| `categories` | `type` | `income`, `expense`, `transfer` |
| `real_estate_properties` | `property_type` | `primary_residence`, `rental`, `vacation`, `commercial` |
| `property_valuations` | `source` | `manual`, `api` |

**Encrypted fields** (run through `encrypt_field()` before insert):

| Table | Encrypted columns |
|---|---|
| `members` | `display_name`, `email` |
| `accounts` | `name`, `institution` |
| `transactions` | `merchant_name`, `memo` |
| `real_estate_properties` | `name`, `address` |

`last_four` on accounts is NOT encrypted (it's used for display). `password_hash` is bcrypt-hashed, not AES-encrypted.

---

## 3. Shared Category Taxonomy

Create these categories once per household (using the household's `household_id`). Set `is_system = True` for all of them. A NULL `parent_category_id` denotes a top-level category. `sort_order` controls display ordering.

The seed script should build a `category_map` dict keyed by a short slug (e.g., `"groceries"`) to easily reference `category_id` values when generating transactions.

### Income categories (`type = 'income'`)

| Slug | Name | Parent |
|---|---|---|
| `income` | Income | — |
| `salary` | Salary & Wages | income |
| `bonus` | Bonus & Commission | income |
| `business_income` | Business Income | — |
| `consulting_fees` | Consulting Fees | business_income |
| `profit_distribution` | Distribution / Profit Share | business_income |
| `investment_income` | Investment Income | — |
| `dividends` | Dividends | investment_income |
| `capital_gains` | Capital Gains | investment_income |
| `rental_income` | Rental Income | — |
| `residential_rental` | Residential Rental | rental_income |
| `short_term_rental` | Short-Term Rental | rental_income |
| `other_income` | Other Income | — |
| `tax_refund` | Tax Refund | other_income |
| `gifts_received` | Gifts Received | other_income |
| `misc_income` | Miscellaneous | other_income |

### Expense categories (`type = 'expense'`)

| Slug | Name | Parent |
|---|---|---|
| `housing` | Housing | — |
| `hoa_fees` | HOA Fees | housing |
| `home_insurance` | Home Insurance | housing |
| `home_maintenance` | Home Maintenance & Repairs | housing |
| `lawn_garden` | Lawn & Garden | housing |
| `cleaning_services` | Cleaning Services | housing |
| `utilities` | Utilities | — |
| `electric` | Electric | utilities |
| `gas_heating` | Gas & Heating | utilities |
| `water_sewer` | Water & Sewer | utilities |
| `internet` | Internet | utilities |
| `cell_phone` | Cell Phone | utilities |
| `streaming` | Streaming Services | utilities |
| `transportation` | Transportation | — |
| `auto_insurance` | Auto Insurance | transportation |
| `gas_fuel` | Gas & Fuel | transportation |
| `car_maintenance` | Car Maintenance | transportation |
| `parking` | Parking | transportation |
| `rideshare` | Rideshare | transportation |
| `ev_charging` | EV Charging | transportation |
| `food_dining` | Food & Dining | — |
| `groceries` | Groceries | food_dining |
| `restaurants` | Restaurants & Takeout | food_dining |
| `coffee` | Coffee Shops | food_dining |
| `food_delivery` | Food Delivery | food_dining |
| `healthcare` | Healthcare | — |
| `health_insurance` | Health Insurance Premium | healthcare |
| `doctor_medical` | Doctor & Medical | healthcare |
| `dental` | Dental | healthcare |
| `vision` | Vision | healthcare |
| `pharmacy` | Prescriptions & Pharmacy | healthcare |
| `fitness` | Fitness & Gym | healthcare |
| `therapy` | Mental Health / Therapy | healthcare |
| `education` | Education & Childcare | — |
| `tuition` | Tuition & School Fees | education |
| `school_supplies` | School Supplies & Books | education |
| `tutoring` | Tutoring & Lessons | education |
| `childcare` | Childcare & After-School | education |
| `student_activities` | Student Activities & Sports | education |
| `personal` | Personal & Shopping | — |
| `clothing` | Clothing & Apparel | personal |
| `personal_care` | Personal Care & Beauty | personal |
| `electronics` | Electronics & Technology | personal |
| `home_goods` | Home Goods & Furnishings | personal |
| `gifts_given` | Gifts Given | personal |
| `entertainment` | Entertainment & Leisure | — |
| `events_tickets` | Events & Tickets | entertainment |
| `travel` | Travel & Vacation | entertainment |
| `hobbies` | Hobbies & Recreation | entertainment |
| `pet_care` | Pet Care | entertainment |
| `subscriptions` | Subscriptions & Memberships | entertainment |
| `property_expenses` | Rental Property Expenses | — |
| `rental_maintenance` | Rental Property Maintenance | property_expenses |
| `property_management` | Property Management Fees | property_management |
| `rental_insurance` | Rental Property Insurance | property_expenses |
| `rental_property_tax` | Rental Property Taxes | property_expenses |
| `business_expenses` | Business Expenses | — |
| `office_supplies` | Office & Supplies | business_expenses |
| `professional_dev` | Professional Development | business_expenses |
| `professional_services` | Professional Services (CPA, Legal) | business_expenses |
| `business_travel` | Business Travel | business_expenses |
| `marketing_software` | Marketing & Software | business_expenses |
| `financial_services` | Financial Services | — |
| `bank_fees` | Bank & Account Fees | financial_services |
| `advisory_fees` | Investment Advisory Fees | financial_services |
| `tax_prep` | Tax Preparation | financial_services |
| `life_insurance` | Life & Umbrella Insurance | financial_services |

### Transfer categories (`type = 'transfer'`)

| Slug | Name | Parent |
|---|---|---|
| `transfers` | Transfers | — |
| `cc_payment` | Credit Card Payment | transfers |
| `loan_payment` | Auto / Personal Loan Payment | transfers |
| `ira_contribution` | IRA Contribution | transfers |
| `brokerage_contribution` | Brokerage Contribution | transfers |
| `savings_transfer` | To / From Savings | transfers |
| `between_accounts` | Between Own Accounts | transfers |
| `mortgage_payment` | Mortgage Payment | transfers |
| `heloc_payment` | HELOC Payment | transfers |

---

## 4. Household 1 — Chen-Nakamura

### Overview

**Demographic context:** A dual-income couple with no dependents in their late 30s / early 40s living in Round Rock, Texas (Austin metro). They represent the top ~12% of US household net worth for their age cohort (35–44), living comfortably but not lavishly. No rental properties, no business income, no dependents. Texas has no state income tax, which simplifies their tax picture. This household exercises basic net worth tracking, two-member RBAC, budget vs. actuals, a FIRE scenario, and a simple debt payoff projection (one auto loan).

**Net worth target:** ~$898,900

### Members

| Field | Primary | Partner |
|---|---|---|
| `display_name` | Wei Chen | Priya Nakamura |
| `email` | wei@chen-nakamura.local | priya@chen-nakamura.local |
| `password_hash` | bcrypt("HearthDemo1!") | bcrypt("HearthDemo1!") |
| `role` | `primary` | `partner` |
| `is_active` | true | true |

### Accounts

All accounts belong to `household_id` = H1's UUID. Fields: `name` (encrypted), `institution` (encrypted), `account_type`, `ownership`, `member_id`, `last_four`, `current_balance`, `is_active`.

| # | Name | Institution | Type | Ownership | Member | Last Four | Current Balance |
|---|---|---|---|---|---|---|---|
| 1 | Primary Checking | Dell Credit Union | `checking` | joint | null | 4821 | 18,200.00 |
| 2 | High-Yield Savings | Marcus by Goldman | `savings` | joint | null | 9312 | 58,200.00 |
| 3 | Dell 401(k) | Fidelity NetBenefits | `retirement_401k` | individual | Wei | 7704 | 210,400.00 |
| 4 | St. David's 403(b) | Vanguard | `retirement_401k` | individual | Priya | 8831 | 95,200.00 |
| 5 | Roth IRA | Fidelity | `retirement_ira` | individual | Wei | 2267 | 48,100.00 |
| 6 | Roth IRA | Vanguard | `retirement_ira` | individual | Priya | 3349 | 32,200.00 |
| 7 | Joint Brokerage | Fidelity | `brokerage` | joint | null | 5513 | 72,800.00 |
| 8 | HSA | Optum Bank | `hsa` | individual | Wei | 6621 | 13,100.00 |
| 9 | Sapphire Preferred | Chase | `credit_card` | joint | null | 9008 | -3,200.00 |
| 10 | RAV4 Auto Loan | Toyota Financial Services | `loan` | individual | Priya | 2205 | -12,400.00 |
| 11 | Home Mortgage | University Federal Credit Union | `mortgage` | joint | null | 7761 | -298,700.00 |
| 12 | Primary Residence | (property valuation account) | `real_estate` | joint | null | — | 665,000.00 |

Account #12 links to the `real_estate_properties` record below. Its `current_balance` should be updated to match the most recent `property_valuations` entry whenever valuations are refreshed.

**Net worth sanity check:**
Assets: 18,200 + 58,200 + 210,400 + 95,200 + 48,100 + 32,200 + 72,800 + 13,100 + 665,000 = **1,213,200**
Liabilities: 3,200 + 12,400 + 298,700 = **314,300**
**Net worth: $898,900** ✓

### Real Estate Property

| Field | Value |
|---|---|
| `name` (encrypted) | 1842 Sunrise Ridge Drive |
| `address` (encrypted) | 1842 Sunrise Ridge Dr, Round Rock, TX 78665 |
| `property_type` | `primary_residence` |
| `acquisition_date` | 2019-03-15 |
| `acquisition_price` | 385,000.0000 |
| `is_active` | true |
| `member_id` | null (joint ownership) |

**Property valuations** (insert all; `source = 'manual'`):

| Date | Amount |
|---|---|
| 2024-01-01 | 598,000.00 |
| 2024-04-01 | 612,000.00 |
| 2024-07-01 | 628,000.00 |
| 2024-10-01 | 641,000.00 |
| 2025-01-01 | 648,000.00 |
| 2025-04-01 | 655,000.00 |
| 2025-07-01 | 658,000.00 |
| 2025-10-01 | 661,000.00 |
| 2026-01-01 | 663,000.00 |
| 2026-06-01 | 665,000.00 |

Austin-area appreciation has cooled from 2021-2022 peaks; moderate 2-4% annual appreciation is realistic here.

### Investment Account Balance Snapshots

Insert monthly snapshots for all retirement/brokerage/HSA accounts. Starting balances (Jan 2024) are back-calculated from current balances assuming contributions and ~9% annual market return (with 2022-2023 recovery). Generate one snapshot per calendar month per account.

| Account | Jan 2024 Balance | Monthly Contribution | Notes |
|---|---|---|---|
| Wei 401(k) | 158,200 | ~$1,917/mo (employee) | Employer matches 4% = ~$383/mo added via payroll |
| Priya 403(b) | 67,400 | ~$1,708/mo | No employer match specified |
| Wei Roth IRA | 34,100 | $500/mo (Jan–Apr each year, then $0 until next Jan) | Annual max $7,000 split over first 5 months |
| Priya Roth IRA | 22,800 | $500/mo (Jan–Apr) | Same pattern |
| Joint Brokerage | 51,200 | $1,000/mo (auto-invest) | Irregular; add $2,000 in June, $0 in Dec |
| HSA | 7,600 | $358/mo | Annual max $4,300 for self-only; payroll contribution |

Use a simplified month-over-month growth formula:
`balance[m] = balance[m-1] × (1 + 0.09/12) + contribution[m]`
with a flat -3% month applied to October 2024 to simulate a brief market dip.

### FIRE Scenario

| Field | Value |
|---|---|
| `name` | "Target 55 FIRE" |
| `member_id` | Wei (primary) |
| `target_retirement_age` | 55 |
| `expected_return_annual` | 0.0700 |
| `inflation_rate_annual` | 0.0300 |
| `target_annual_spend` | 95,000.0000 |

`additional_income_streams` JSONB array:

```json
[
  {
    "id": "<uuid>",
    "label": "Wei — Dell salary",
    "type": "salary",
    "amount_annual": 115000.00,
    "start_year": 2024,
    "end_year": 2040,
    "growth_rate_annual": 0.03
  },
  {
    "id": "<uuid>",
    "label": "Priya — RN salary",
    "type": "salary",
    "amount_annual": 98000.00,
    "start_year": 2024,
    "end_year": 2039,
    "growth_rate_annual": 0.02
  },
  {
    "id": "<uuid>",
    "label": "Wei Social Security (age 67)",
    "type": "social_security",
    "amount_annual": 38000.00,
    "start_year": 2051,
    "end_year": null,
    "growth_rate_annual": 0.025
  },
  {
    "id": "<uuid>",
    "label": "Priya Social Security (age 67)",
    "type": "social_security",
    "amount_annual": 32000.00,
    "start_year": 2053,
    "end_year": null,
    "growth_rate_annual": 0.025
  }
]
```

### Debt Payoff Scenario

| Field | Value |
|---|---|
| `account_id` | RAV4 Auto Loan (Account #10) |
| `strategy` | `avalanche` |
| `extra_monthly_payment` | 200.0000 |

### Monthly Income Pattern (30-month range, all to Account #1 — Primary Checking)

Wei and Priya are paid biweekly (26 paychecks/year each). For simplicity, model as two deposits per month on the 7th and 21st (Wei) and 1st and 15th (Priya). In months where a 3rd paycheck occurs (happens twice/year per earner), add the extra deposit.

| Payer | Frequency | Net Per Paycheck | Category | Merchant |
|---|---|---|---|---|
| Dell Technologies | Biweekly (7th + 21st) | $3,425.00 | `salary` | "Dell Technologies Payroll" |
| St. David's HealthCare | Biweekly (1st + 15th) | $2,875.00 | `salary` | "Ascension Health Payroll" |

Additionally: each April, a federal tax refund of $2,100 deposits to checking (`tax_refund` category, "IRS TREAS 310"). Texas has no state refund.

### Monthly Expense & Transfer Pattern

Generate individual transactions from these patterns. All credit card expenses hit Account #9 (Chase Sapphire); all direct debits hit Account #1 (Checking). At the end of each month (28th–30th), generate a credit card payment transfer from Checking → Chase Sapphire for the approximate statement balance.

**Fixed monthly transactions (checking, same amount each month):**

| Merchant | Category | Amount | Account | Notes |
|---|---|---|---|---|
| University Federal CU | `mortgage_payment` | $1,828.00 | Checking | Transfer to mortgage account; P+I only, no escrow |
| City of Round Rock Utilities | `water_sewer` | $62.00 | Checking | Direct debit |
| Oncor Electric | `electric` | $142.00 (summer: $195) | Checking | Seasonal adjustment Jun–Sep |
| TXU / Atmos Gas | `gas_heating` | $38.00 (winter: $89) | Checking | Seasonal Nov–Feb |
| Fidelity Auto-Invest | `brokerage_contribution` | $1,000.00 | Checking | Transfer to Account #7 (brokerage) |
| Toyota Financial Services | `loan_payment` | $312.00 | Checking | Transfer to Account #10 |
| Priya — Roth IRA (Jan–May) | `ira_contribution` | $1,400.00 | Checking | Transfer to Account #6; Jan, Feb, Mar, Apr, May only |
| Wei — Roth IRA (Jan–May) | `ira_contribution` | $1,400.00 | Checking | Transfer to Account #5; Jan, Feb, Mar, Apr, May only |

**Variable monthly transactions (credit card, amounts with ±10% jitter):**

| Category | Merchant Examples | Monthly Range | Frequency |
|---|---|---|---|
| `groceries` | H-E-B, Costco, Trader Joe's | $680–$820 | 6–8 transactions |
| `restaurants` | Local Austin spots, Chuy's, Torchy's | $280–$420 | 4–7 transactions |
| `coffee` | Starbucks, local cafes | $55–$95 | 4–8 transactions |
| `food_delivery` | DoorDash, Uber Eats | $45–$90 | 2–4 transactions |
| `gas_fuel` | HEB Gas, Shell | $140–$180 | 3–5 transactions |
| `internet` | AT&T Fiber | $75.00 (fixed) | 1 transaction |
| `cell_phone` | T-Mobile | $110.00 (fixed) | 1 transaction |
| `streaming` | Netflix, Spotify, Disney+ | $52.00 (fixed) | 3 transactions |
| `auto_insurance` | USAA Auto | $186.00 (fixed) | 1 transaction |
| `home_insurance` | USAA Home | $165.00 (fixed) | 1 transaction (paid monthly via escrow — model as credit card, Jan only for annual renew memo) |
| `fitness` | Lifetime Fitness | $89.00 (fixed) | 1 transaction |
| `clothing` | Target, Amazon | $85–$200 | 1–3 transactions |
| `personal_care` | Salon, pharmacy | $60–$120 | 2–3 transactions |
| `subscriptions` | Amazon Prime, NYT, Xbox | $38.00 | 3 transactions |
| `events_tickets` | Alamo Drafthouse, concerts | $80–$200 | 1–3 transactions |
| `home_maintenance` | Home Depot, Lowe's | $50–$300 | 0–2 transactions (skip some months) |
| `pharmacy` | CVS, Walgreens | $25–$65 | 1–2 transactions |
| `electronics` | Best Buy, Apple | $0–$400 | 0–1 transactions (occasional, Q2 and Q4 lean higher) |

**Seasonal / annual expenses (add on specific months):**

| Month(s) | Category | Merchant | Amount | Notes |
|---|---|---|---|---|
| March | `travel` | Southwest Airlines, VRBO | $1,800–$2,400 | Spring trip (South Padre or New Orleans) |
| July | `travel` | Delta, Marriott | $2,200–$3,100 | Summer trip (Pacific Northwest) |
| November | `travel` | Various | $600–$900 | Thanksgiving trip to family (flights) |
| December | `gifts_given` | Amazon, local shops | $800–$1,200 | Holiday gifts |
| April | `tax_prep` | TurboTax / H&R Block | $180.00 | Annual |
| January | `home_maintenance` | Pest control / HVAC service | $250.00 | Annual service contracts |
| June | `lawn_garden` | SiteOne Landscape / nursery | $150–$350 | Spring yard projects |

### Budget Configuration

Set budgets effective `2024-01-01`. Use `Decimal` values.

| Category | Monthly Budget |
|---|---|
| `groceries` | 750.00 |
| `restaurants` | 350.00 |
| `coffee` | 75.00 |
| `food_delivery` | 60.00 |
| `gas_fuel` | 160.00 |
| `electric` | 155.00 |
| `internet` | 75.00 |
| `cell_phone` | 110.00 |
| `streaming` | 52.00 |
| `auto_insurance` | 186.00 |
| `fitness` | 89.00 |
| `clothing` | 120.00 |
| `personal_care` | 90.00 |
| `events_tickets` | 120.00 |
| `home_maintenance` | 150.00 |
| `travel` | 400.00 |
| `gifts_given` | 100.00 |
| `subscriptions` | 38.00 |
| `pharmacy` | 50.00 |

Add a second budget row for `groceries` effective `2025-01-01` with amount `780.00` to demonstrate the budget history / effective_from functionality.

---

## 5. Household 2 — Okonkwo-Rivera

### Overview

**Demographic context:** A four-member family (two adults + two teenage dependents) in Naperville, Illinois — one of the wealthiest suburbs of Chicago. Darius is a senior partner at a boutique law firm; Carmen is an assistant superintendent at a large suburban school district. They own a primary home plus a rental condo purchased before buying the house. Their finances exercise: four-member RBAC (dependents can view joint accounts), rental property P&L, 529 college savings tracking (as brokerage accounts), multiple checking and savings accounts, and a more complex FIRE model that includes rental income and a defined-benefit pension stream.

**Net worth target:** ~$3,407,800

### Members

| Field | Primary | Partner | Dependent 1 | Dependent 2 |
|---|---|---|---|---|
| `display_name` | Darius Okonkwo | Carmen Rivera-Okonkwo | Emma Okonkwo | Noah Okonkwo |
| `email` | darius@okonkwo-rivera.local | carmen@okonkwo-rivera.local | emma@okonkwo-rivera.local | noah@okonkwo-rivera.local |
| `role` | `primary` | `partner` | `dependent` | `dependent` |
| `is_active` | true | true | true | true |

Emma and Noah have `dependent` role — they can view joint accounts but have no individual accounts of their own in HearthLedger.

### Accounts

| # | Name | Institution | Type | Ownership | Member | Last Four | Current Balance |
|---|---|---|---|---|---|---|---|
| 1 | Premier Plus Checking | Chase | `checking` | joint | null | 5589 | 35,200.00 |
| 2 | Savings | Chase | `savings` | joint | null | 6712 | 52,400.00 |
| 3 | Online Savings | Ally Bank | `savings` | joint | null | 3881 | 118,000.00 |
| 4 | 401(k) | Fidelity NetBenefits | `retirement_401k` | individual | Darius | 4405 | 920,500.00 |
| 5 | 403(b) | TIAA | `retirement_401k` | individual | Carmen | 7723 | 385,200.00 |
| 6 | Roth IRA | Fidelity | `retirement_ira` | individual | Darius | 8834 | 84,200.00 |
| 7 | Roth IRA | Vanguard | `retirement_ira` | individual | Carmen | 9921 | 67,800.00 |
| 8 | Joint Brokerage | Schwab | `brokerage` | joint | null | 2267 | 660,400.00 |
| 9 | 529 — Emma | Illinois Bright Start | `brokerage` | joint | null | 3306 | 94,600.00 |
| 10 | 529 — Noah | Illinois Bright Start | `brokerage` | joint | null | 3307 | 70,200.00 |
| 11 | HSA | HSA Bank | `hsa` | joint | null | 8872 | 25,600.00 |
| 12 | Sapphire Reserve | Chase | `credit_card` | joint | null | 1188 | -4,850.00 |
| 13 | Amazon Prime Visa | Chase | `credit_card` | joint | null | 4456 | -1,650.00 |
| 14 | VW ID.4 Auto Loan | Volkswagen Financial | `loan` | individual | Darius | 5543 | -22,800.00 |
| 15 | Toyota RAV4 Loan | Toyota Financial | `loan` | individual | Carmen | 6621 | -16,400.00 |
| 16 | Primary Home Mortgage | Wells Fargo | `mortgage` | joint | null | 9905 | -512,400.00 |
| 17 | Evanston Condo Mortgage | Chase Mortgage | `mortgage` | joint | null | 1122 | -261,200.00 |
| 18 | Primary Residence | (property valuation) | `real_estate` | joint | null | — | 1,225,000.00 |
| 19 | Evanston Rental Condo | (property valuation) | `real_estate` | joint | null | — | 488,000.00 |

**Net worth sanity check:**
Assets: 35,200 + 52,400 + 118,000 + 920,500 + 385,200 + 84,200 + 67,800 + 660,400 + 94,600 + 70,200 + 25,600 + 1,225,000 + 488,000 = **4,227,100**
Liabilities: 4,850 + 1,650 + 22,800 + 16,400 + 512,400 + 261,200 = **819,300**
**Net worth: $3,407,800** ✓

### Account Access Grants

Dependents (Emma and Noah) should not have individual accounts, but HearthLedger's RBAC allows dependents to view joint accounts automatically. No explicit `account_access_grants` rows needed for this standard case — the `AccountRepository.get_visible(ctx)` logic handles it. However, insert a grant so that Carmen can additionally view Account #4 (Darius's 401k), modeling the real-world situation where the partner spouse tracks the primary's retirement balance:

| Granted Account | Granted To | Granted By |
|---|---|---|
| Account #4 (Darius 401k) | Carmen | Darius |

### Real Estate Properties

**Property 1 — Primary Residence:**

| Field | Value |
|---|---|
| `name` (encrypted) | 2614 Whispering Pines Drive |
| `address` (encrypted) | 2614 Whispering Pines Dr, Naperville, IL 60564 |
| `property_type` | `primary_residence` |
| `acquisition_date` | 2018-09-14 |
| `acquisition_price` | 780,000.0000 |

Valuations:

| Date | Amount |
|---|---|
| 2024-01-01 | 1,138,000.00 |
| 2024-07-01 | 1,162,000.00 |
| 2025-01-01 | 1,192,000.00 |
| 2025-07-01 | 1,210,000.00 |
| 2026-01-01 | 1,220,000.00 |
| 2026-06-01 | 1,225,000.00 |

**Property 2 — Evanston Rental Condo:**

| Field | Value |
|---|---|
| `name` (encrypted) | 1847 Dempster St Unit 3C |
| `address` (encrypted) | 1847 Dempster St #3C, Evanston, IL 60201 |
| `property_type` | `rental` |
| `acquisition_date` | 2014-05-20 |
| `acquisition_price` | 310,000.0000 |

Valuations:

| Date | Amount |
|---|---|
| 2024-01-01 | 445,000.00 |
| 2024-07-01 | 460,000.00 |
| 2025-01-01 | 472,000.00 |
| 2025-07-01 | 481,000.00 |
| 2026-01-01 | 486,000.00 |
| 2026-06-01 | 488,000.00 |

The rental condo has one tenant paying $2,650/month. Rental income transactions (tagged to Property 2's `real_estate_property_id`) deposit on the 1st of each month to Account #1 (Checking). Occasional months (model 2 over the 30-month window, e.g., August 2024 and March 2025) have a one-week late payment, depositing on the 8th instead of the 1st.

### Investment Account Balance Snapshots

| Account | Jan 2024 | Monthly Contribution | Notes |
|---|---|---|---|
| Darius 401(k) | 741,000 | $2,542/mo employee (max + catch-up $30,500 ÷ 12) | Firm matches 3% of salary = ~$713/mo additional |
| Carmen 403(b) | 303,200 | $1,917/mo (max $23,000 ÷ 12) | No employer match for public admin 403b |
| Darius Roth IRA | 65,400 | $583/mo (Jan–Oct only; 2025 max $7,000 ÷ 10) | Backdoor Roth; note high income makes direct ineligible |
| Carmen Roth IRA | 52,200 | $583/mo (Jan–Oct) | Same |
| Schwab Joint Brokerage | 465,000 | $2,500/mo | Irregular; add $10,000 in March (bonus allocation) |
| Emma 529 | 70,200 | $500/mo | Starting balance reflects 10 years of contributions |
| Noah 529 | 48,600 | $500/mo | Starting balance reflects 7 years of contributions |
| HSA | 15,800 | $646/mo (family max $7,750 ÷ 12) | |

Use same growth formula as H1 (9% annual), with a -4% dip in October 2024 for the brokerage account.

### FIRE Scenarios

**Scenario A — "Retire at 60"** (Darius's target)

| Field | Value |
|---|---|
| `name` | "Retire at 60" |
| `member_id` | Darius |
| `target_retirement_age` | 60 |
| `expected_return_annual` | 0.0650 |
| `inflation_rate_annual` | 0.0300 |
| `target_annual_spend` | 220,000.0000 |

Income streams:
```json
[
  {"id": "<uuid>", "label": "Darius — Law Firm Income", "type": "salary", "amount_annual": 285000.00, "start_year": 2024, "end_year": 2038, "growth_rate_annual": 0.03},
  {"id": "<uuid>", "label": "Carmen — School District", "type": "salary", "amount_annual": 130000.00, "start_year": 2024, "end_year": 2038, "growth_rate_annual": 0.025},
  {"id": "<uuid>", "label": "Evanston Rental — Net", "type": "rental", "amount_annual": 24000.00, "start_year": 2024, "end_year": null, "growth_rate_annual": 0.02},
  {"id": "<uuid>", "label": "Carmen IMRF Pension (age 62)", "type": "pension", "amount_annual": 72000.00, "start_year": 2044, "end_year": null, "growth_rate_annual": 0.00},
  {"id": "<uuid>", "label": "Darius Social Security (age 67)", "type": "social_security", "amount_annual": 48000.00, "start_year": 2045, "end_year": null, "growth_rate_annual": 0.025},
  {"id": "<uuid>", "label": "Carmen Social Security (age 67)", "type": "social_security", "amount_annual": 36000.00, "start_year": 2047, "end_year": null, "growth_rate_annual": 0.025}
]
```

**Scenario B — "Aggressive FIRE at 55"** (Darius's stretch goal)

| Field | Value |
|---|---|
| `name` | "Aggressive FIRE at 55" |
| `member_id` | Darius |
| `target_retirement_age` | 55 |
| `expected_return_annual` | 0.0700 |
| `inflation_rate_annual` | 0.0300 |
| `target_annual_spend` | 180,000.0000 |

Income streams: same rental and Social Security streams as Scenario A, but with salary streams ending 2033.

### Debt Payoff Scenarios

| Account | Strategy | Extra Monthly Payment |
|---|---|---|
| Darius — VW ID.4 (Account #14) | `avalanche` | 300.00 |
| Carmen — Toyota (Account #15) | `avalanche` | 200.00 |

Model: avalanche strategy pays off the higher-rate loan first (VW ID.4 at ~6.9% APR), then applies combined extra payment to the Toyota.

### Monthly Income Pattern

| Payer | Deposit Date(s) | Net Amount | Account | Category | Merchant |
|---|---|---|---|---|---|
| Feldman & Okonkwo LLP (draw) | 1st of month | $13,000.00 | Checking | `salary` | "Feldman & Okonkwo LLP Payroll" |
| Naperville CUSD 203 | 1st and 15th | $2,875.00 each | Checking | `salary` | "CUSD 203 Payroll" |
| Evanston Condo Tenant | 1st of month | $2,650.00 | Checking | `residential_rental` | "ACH Tenant Payment" |
| F&O LLP — Year-End Bonus | December 15 | $80,000.00 | Checking | `profit_distribution` | "Feldman & Okonkwo Year-End Distribution" |
| **Illinois tax refund** | March (once/year) | $3,200.00 | Checking | `tax_refund` | "Illinois Dept of Revenue" |

Tag all rental income transactions to Property 2's `real_estate_property_id`.

### Monthly Expense & Transfer Pattern

**Fixed monthly (checking debits):**

| Merchant | Category | Amount | Notes |
|---|---|---|---|
| Wells Fargo Mortgage | `mortgage_payment` | $3,620.00 | Transfer to Account #16 |
| Chase Mortgage | `mortgage_payment` | $1,352.00 | Transfer to Account #17 (rental condo mortgage) — tag to Property 2 |
| Toyota Financial | `loan_payment` | $462.00 | Transfer to Account #15 |
| Volkswagen Financial | `loan_payment` | $548.00 | Transfer to Account #14 |
| Schwab Auto-Invest | `brokerage_contribution` | $2,500.00 | Transfer to Account #8 |
| IL Bright Start — Emma | `brokerage_contribution` | $500.00 | Transfer to Account #9 |
| IL Bright Start — Noah | `brokerage_contribution` | $500.00 | Transfer to Account #10 |
| CC Payment — Sapphire Reserve | `cc_payment` | (statement balance) | Transfer Checking → Account #12 |
| CC Payment — Amazon Prime | `cc_payment` | (statement balance) | Transfer Checking → Account #13 |

**Variable monthly (split across Chase Sapphire Reserve and Amazon Prime Visa):**

| Category | Merchant Examples | Monthly Range | Primary Card |
|---|---|---|---|
| `groceries` | Jewel-Osco, Costco, Trader Joe's, Whole Foods | $1,050–$1,280 | Amazon Prime Visa (Whole Foods 5% back) |
| `restaurants` | Lou Malnati's, Wildfire, local Naperville | $480–$680 | Sapphire Reserve (3x dining) |
| `coffee` | Starbucks, Intelligentsia | $85–$130 | Sapphire Reserve |
| `food_delivery` | Grubhub, DoorDash | $120–$200 | Sapphire Reserve |
| `gas_fuel` | BP, Shell | $280–$360 | Sapphire Reserve (3x gas) |
| `internet` | Comcast Xfinity | $95.00 | Checking (direct debit) |
| `cell_phone` | Verizon | $185.00 | Amazon Prime |
| `streaming` | Netflix, Peacock, Apple TV+, Spotify | $68.00 | Amazon Prime |
| `electric` | ComEd | $165.00 (summer: $230) | Checking |
| `gas_heating` | Nicor Gas | $45.00 (winter: $220) | Checking |
| `auto_insurance` | State Farm (two cars) | $298.00 | Checking |
| `home_insurance` | Allstate | $212.00 | Checking |
| `fitness` | Lifetime Fitness Naperville | $125.00 | Sapphire Reserve |
| `clothing` | Nordstrom, Gap, Target | $200–$450 | Sapphire Reserve |
| `personal_care` | Salons, dry cleaning, pharmacy | $180–$280 | Sapphire Reserve |
| `school_supplies` | Staples, Target | $40–$120 | Amazon Prime |
| `student_activities` | Sports fees, band, clubs | $150–$350 | Checking |
| `events_tickets` | Goodman Theatre, Cubs, concerts | $200–$450 | Sapphire Reserve |
| `subscriptions` | Amazon Prime, Hulu, Audible | $48.00 | Amazon Prime |
| `home_maintenance` | Ace Hardware, contractors | $150–$600 | Checking |
| `cleaning_services` | Molly Maid (biweekly) | $280.00 | Checking |

**Rental property expenses** (tag to Property 2, via Checking or Sapphire Reserve):

| Category | Merchant | Amount | Frequency |
|---|---|---|---|
| `rental_maintenance` | Various contractors | $200–$800 | 1–2 per quarter |
| `property_management` | (self-managed, no fee) | — | — |
| `rental_insurance` | State Farm Landlord | $125.00 | Monthly |
| `rental_property_tax` | Cook County Treasurer | $2,850.00 | Twice/year (March and September) |

**Seasonal / annual:**

| Month(s) | Category | Merchant | Amount |
|---|---|---|---|
| March | `travel` | American Airlines, VRBO/Marriott | $3,800–$5,200 |
| July | `travel` | Delta, resort hotel | $4,500–$6,800 |
| August | `tuition` | Northwestern summer program (Emma) | $3,200 |
| October | `events_tickets` | Cubs NLCS / other fall events | $400–$900 |
| December | `gifts_given` | Amazon, local merchants | $1,800–$2,800 |
| April | `tax_prep` | CPA firm | $2,400 |
| January | `advisory_fees` | Schwab Portfolio Advisory | $850 |

### Budget Configuration (effective 2024-01-01)

| Category | Monthly Budget |
|---|---|
| `groceries` | 1,150.00 |
| `restaurants` | 550.00 |
| `coffee` | 100.00 |
| `food_delivery` | 150.00 |
| `gas_fuel` | 320.00 |
| `internet` | 95.00 |
| `cell_phone` | 185.00 |
| `streaming` | 68.00 |
| `electric` | 195.00 |
| `auto_insurance` | 298.00 |
| `home_insurance` | 212.00 |
| `fitness` | 125.00 |
| `clothing` | 300.00 |
| `personal_care` | 230.00 |
| `cleaning_services` | 280.00 |
| `student_activities` | 250.00 |
| `events_tickets` | 300.00 |
| `home_maintenance` | 300.00 |
| `travel` | 600.00 |
| `gifts_given` | 200.00 |
| `subscriptions` | 48.00 |

Add a budget update for `restaurants` effective `2025-03-01`: amount `650.00` (reflecting inflation and lifestyle creep). This exercises the budget history query.

---

## 6. Household 3 — Whitfield-Torres

### Overview

**Demographic context:** A high-income Los Angeles household in Brentwood (West LA), approaching potential semi-retirement. Benjamin is the founding partner of a boutique entertainment law firm; Gabriela is an independent real estate development consultant working through her own LLC. They have two children: Sophia (22, a recent USC film graduate now working at a streaming company) has been granted partner-level access to help manage family finances — exercising the `account_access_grants` table — and Ethan (19, a UCSB sophomore). Three real estate properties create meaningful P&L reporting. Combined household income crosses the California millionaire's tax threshold, adding a 13.3% effective state rate on top income. This household exercises: complex RBAC with an adult dependent having elevated access, three-property P&L, multi-source FIRE modeling, HELOC tracking, a SEP-IRA (self-employed), and premium credit card spending patterns consistent with $1M+ household income.

**Net worth target:** ~$9,463,400

### Members

| Field | Primary | Partner | Dependent 1 | Dependent 2 |
|---|---|---|---|---|
| `display_name` | Benjamin Whitfield | Gabriela Torres-Whitfield | Sophia Whitfield | Ethan Torres-Whitfield |
| `email` | ben@whitfield-torres.local | gabriela@whitfield-torres.local | sophia@whitfield-torres.local | ethan@whitfield-torres.local |
| `role` | `primary` | `partner` | `dependent` | `dependent` |
| `is_active` | true | true | true | true |

### Account Access Grants

Sophia (`dependent` role) should be granted explicit partner-level visibility on joint accounts so she can help manage finances. Insert the following `account_access_grants` rows:

| Granted Account | Granted To | Granted By | Notes |
|---|---|---|---|
| Account #1 (JPM Joint Checking) | Sophia | Benjamin | Views for bill monitoring |
| Account #2 (Chase Savings) | Sophia | Benjamin | Views for cash management |
| Account #9 (Schwab Joint Brokerage) | Sophia | Benjamin | Views investment performance |

Ethan has no grants beyond the joint-account read access that all dependents receive.

### Accounts

| # | Name | Institution | Type | Ownership | Member | Last Four | Current Balance |
|---|---|---|---|---|---|---|---|
| 1 | Private Client Checking | JPMorgan Chase | `checking` | joint | null | 3847 | 72,400.00 |
| 2 | Private Client Savings | JPMorgan Chase | `savings` | joint | null | 5512 | 145,000.00 |
| 3 | Investor Checking | Charles Schwab | `checking` | individual | Benjamin | 7723 | 38,500.00 |
| 4 | Money Market (VMFXX) | Vanguard | `savings` | joint | null | 2241 | 168,000.00 |
| 5 | 401(k) / Profit-Sharing Plan | Fidelity | `retirement_401k` | individual | Benjamin | 8834 | 1,920,400.00 |
| 6 | SEP-IRA | Charles Schwab | `retirement_ira` | individual | Gabriela | 9905 | 695,200.00 |
| 7 | Roth IRA | Fidelity | `retirement_ira` | individual | Benjamin | 4421 | 118,400.00 |
| 8 | Roth IRA | Vanguard | `retirement_ira` | individual | Gabriela | 5536 | 98,600.00 |
| 9 | Joint Taxable Brokerage | Charles Schwab | `brokerage` | joint | null | 6647 | 1,580,500.00 |
| 10 | Individual Brokerage | Fidelity | `brokerage` | individual | Benjamin | 7758 | 568,200.00 |
| 11 | Roth IRA | Fidelity | `retirement_ira` | individual | Sophia | 1102 | 12,400.00 |
| 12 | 529 College Savings | ScholarShare (CA) | `brokerage` | joint | null | 2213 | 88,400.00 |
| 13 | HSA | Fidelity | `hsa` | joint | null | 3324 | 44,200.00 |
| 14 | Platinum Card | American Express | `credit_card` | individual | Benjamin | 9981 | -8,200.00 |
| 15 | Gold Card | American Express | `credit_card` | individual | Gabriela | 4472 | -3,800.00 |
| 16 | Sapphire Reserve | Chase | `credit_card` | joint | null | 5583 | -2,400.00 |
| 17 | Primary Home Mortgage | JPMorgan Chase Private | `mortgage` | joint | null | 8891 | -1,285,000.00 |
| 18 | Silver Lake Duplex Mortgage | Wells Fargo | `mortgage` | joint | null | 9902 | -645,200.00 |
| 19 | Palm Springs Mortgage | LoanDepot | `mortgage` | joint | null | 1123 | -418,600.00 |
| 20 | HELOC | Chase | `loan` | joint | null | 4437 | -92,000.00 |
| 21 | Tesla Model X | Tesla Financial | `loan` | individual | Benjamin | 5548 | -38,200.00 |
| 22 | Porsche Cayenne | Porsche Financial | `loan` | individual | Gabriela | 6659 | -28,400.00 |
| 23 | Brentwood Primary Residence | (property valuation) | `real_estate` | joint | null | — | 4,100,000.00 |
| 24 | Silver Lake Duplex | (property valuation) | `real_estate` | joint | null | — | 1,350,000.00 |
| 25 | Palm Springs Vacation Rental | (property valuation) | `real_estate` | joint | null | — | 985,000.00 |

**Net worth sanity check:**
Assets: 72,400 + 145,000 + 38,500 + 168,000 + 1,920,400 + 695,200 + 118,400 + 98,600 + 1,580,500 + 568,200 + 12,400 + 88,400 + 44,200 + 4,100,000 + 1,350,000 + 985,000 = **11,985,200**
Liabilities: 8,200 + 3,800 + 2,400 + 1,285,000 + 645,200 + 418,600 + 92,000 + 38,200 + 28,400 = **2,521,800**
**Net worth: $9,463,400** ✓

### Real Estate Properties

**Property 1 — Primary Residence (Brentwood):**

| Field | Value |
|---|---|
| `name` (encrypted) | 12847 Corsair Way |
| `address` (encrypted) | 12847 Corsair Way, Los Angeles, CA 90049 |
| `property_type` | `primary_residence` |
| `acquisition_date` | 2020-11-12 |
| `acquisition_price` | 3,200,000.0000 |

Valuations:

| Date | Amount |
|---|---|
| 2024-01-01 | 3,750,000.00 |
| 2024-07-01 | 3,850,000.00 |
| 2025-01-01 | 3,980,000.00 |
| 2025-07-01 | 4,050,000.00 |
| 2026-01-01 | 4,090,000.00 |
| 2026-06-01 | 4,100,000.00 |

**Property 2 — Silver Lake Duplex:**

| Field | Value |
|---|---|
| `name` (encrypted) | 2218–2220 Marathon Street |
| `address` (encrypted) | 2218 Marathon St, Los Angeles, CA 90026 |
| `property_type` | `rental` |
| `acquisition_date` | 2017-08-22 |
| `acquisition_price` | 1,050,000.0000 |

Valuations:

| Date | Amount |
|---|---|
| 2024-01-01 | 1,240,000.00 |
| 2024-07-01 | 1,280,000.00 |
| 2025-01-01 | 1,310,000.00 |
| 2025-07-01 | 1,335,000.00 |
| 2026-01-01 | 1,345,000.00 |
| 2026-06-01 | 1,350,000.00 |

Rental details: Unit A (upper, 2BR/1BA) — $3,200/mo; Unit B (lower, 2BR/1BA) — $2,950/mo. Total: $6,150/mo gross rental income. One unit vacant in November 2024 (Unit B, tenant moved out; new tenant started December 1) — model as $0 income for Unit B in November only.

**Property 3 — Palm Springs Vacation Rental:**

| Field | Value |
|---|---|
| `name` (encrypted) | 78456 Desert Hills Drive |
| `address` (encrypted) | 78456 Desert Hills Dr, Palm Springs, CA 92264 |
| `property_type` | `vacation` |
| `acquisition_date` | 2021-06-08 |
| `acquisition_price` | 1,085,000.0000 |

Valuations:

| Date | Amount |
|---|---|
| 2024-01-01 | 1,040,000.00 |
| 2024-07-01 | 1,020,000.00 |
| 2025-01-01 | 1,000,000.00 |
| 2025-07-01 | 988,000.00 |
| 2026-01-01 | 983,000.00 |
| 2026-06-01 | 985,000.00 |

STR rental income (seasonal; tag to Property 3). High season: January–April and October–November. Low season: May–September. Personal use: June and most of July (no rental income those months).

| Month Pattern | Gross STR Income | Notes |
|---|---|---|
| Jan, Feb, Mar, Apr | $5,800–$7,200 | High season; 18–22 nights booked |
| May | $2,400–$3,200 | Shoulder |
| June | $0 | Personal use |
| July | $0 | Primarily personal use |
| August, September | $1,800–$2,600 | Low season |
| October, November | $4,200–$5,800 | Fall high season |
| December | $3,200–$4,400 | Holiday season |

### Investment Account Balance Snapshots

| Account | Jan 2024 | Monthly Contribution | Notes |
|---|---|---|---|
| Benjamin 401k/Profit-Sharing | 1,492,000 | $2,708/mo employee + ~$5,200/mo profit-share | Profit-sharing contribution arrives as one lump sum in January each year: $62,000 (2024) and $65,000 (2025) |
| Gabriela SEP-IRA | 508,000 | One annual contribution in January: $66,000 (2024), $69,000 (2025) | SEP-IRA max = 25% of net self-employment income, capped at ~$69K |
| Benjamin Roth IRA | 88,200 | $583/mo (Jan–Oct; backdoor Roth) | |
| Gabriela Roth IRA | 73,600 | $583/mo (Jan–Oct; backdoor Roth) | |
| Schwab Joint Brokerage | 1,175,000 | $5,000/mo | Add $50,000 in January each year (year-end transfer from operations) |
| Benjamin Individual Brokerage | 421,000 | $2,000/mo | Irregular; add $30,000 in Q4 each year |
| Sophia Roth IRA | 4,800 | $500/mo (Jan–Dec; Sophia earns ~$62K/yr so is eligible; Ben funds it as a gift) | Started Jan 2024 |
| Ethan 529 | 60,000 | $2,333/mo until July 2025, then $0 (account approaches target as Ethan transfers to UC) | Annual contribution $28,000 for 2024; $14,000 in 2025 |
| HSA | 28,400 | $646/mo (family max) | |

Apply a -5% one-month dip to Schwab Joint Brokerage and Benjamin Individual Brokerage in October 2024 (market correction). Apply a -3% dip in April 2025 to reflect tariff volatility.

### FIRE Scenarios

**Scenario A — "Coast at 58 / Semi-Retirement"** (Benjamin's plan)

| Field | Value |
|---|---|
| `name` | "Coast at 58 — Semi-Retirement" |
| `member_id` | Benjamin |
| `target_retirement_age` | 58 |
| `expected_return_annual` | 0.0650 |
| `inflation_rate_annual` | 0.0300 |
| `target_annual_spend` | 420,000.0000 |

Income streams:
```json
[
  {
    "id": "<uuid>",
    "label": "Ben — Law Firm (until 58)",
    "type": "salary",
    "amount_annual": 650000.00,
    "start_year": 2024,
    "end_year": 2030,
    "growth_rate_annual": 0.04
  },
  {
    "id": "<uuid>",
    "label": "Gabriela — Consulting (full)",
    "type": "consulting",
    "amount_annual": 385000.00,
    "start_year": 2024,
    "end_year": 2030,
    "growth_rate_annual": 0.03
  },
  {
    "id": "<uuid>",
    "label": "Gabriela — Consulting (reduced, post-56)",
    "type": "consulting",
    "amount_annual": 120000.00,
    "start_year": 2030,
    "end_year": null,
    "growth_rate_annual": 0.02
  },
  {
    "id": "<uuid>",
    "label": "Silver Lake Duplex — Net Rental",
    "type": "rental",
    "amount_annual": 58000.00,
    "start_year": 2024,
    "end_year": null,
    "growth_rate_annual": 0.02
  },
  {
    "id": "<uuid>",
    "label": "Palm Springs STR — Net",
    "type": "rental",
    "amount_annual": 32000.00,
    "start_year": 2024,
    "end_year": null,
    "growth_rate_annual": 0.01
  },
  {
    "id": "<uuid>",
    "label": "Benjamin Social Security (age 70)",
    "type": "social_security",
    "amount_annual": 65000.00,
    "start_year": 2042,
    "end_year": null,
    "growth_rate_annual": 0.025
  },
  {
    "id": "<uuid>",
    "label": "Gabriela Social Security (age 70)",
    "type": "social_security",
    "amount_annual": 52000.00,
    "start_year": 2044,
    "end_year": null,
    "growth_rate_annual": 0.025
  }
]
```

**Scenario B — "True FIRE Now (Stress Test)"**

| Field | Value |
|---|---|
| `name` | "True FIRE — Stress Test" |
| `member_id` | Benjamin |
| `target_retirement_age` | 54 |
| `expected_return_annual` | 0.0550 |
| `inflation_rate_annual` | 0.0350 |
| `target_annual_spend` | 380,000.0000 |

Income streams: rentals + Social Security only (no salary/consulting). This tests a conservative scenario with maximum dependence on investable assets.

### Debt Payoff Scenario

| Account | Strategy | Extra Monthly Payment | Notes |
|---|---|---|---|
| Tesla Model X (Account #21) | `avalanche` | 500.00 | Higher rate (7.9% APR from 2023) |

The Porsche loan (Account #22, 3.9% APR) is not included in the debt scenario — they're comfortable with the lower rate.

### Monthly Income Pattern

| Payer | Deposit Date | Net Amount | Account | Category | Merchant |
|---|---|---|---|---|---|
| Whitfield & Associates LLP (salary draw) | 1st of month | $18,500.00 | JPM Checking (#1) | `salary` | "Whitfield & Associates LLP" |
| Torres Development Consulting LLC (monthly) | 15th of month | $24,000.00 | JPM Checking (#1) | `consulting_fees` | "Torres Dev Consulting LLC" |
| W&A LLP Annual Distribution | October 20 | $120,000.00 | Schwab Checking (#3) | `profit_distribution` | "W&A LLP Partner Distribution" |
| Silver Lake — Unit A | 1st of month | $3,200.00 | JPM Checking (#1) | `residential_rental` | "Tenant ACH — Unit A" |
| Silver Lake — Unit B | 1st of month | $2,950.00 | JPM Checking (#1) | `residential_rental` | "Tenant ACH — Unit B" |
| Palm Springs STR | 15th of month (lagged) | (see seasonal table above) | JPM Checking (#1) | `short_term_rental` | "Airbnb Payout" |
| CA Tax Refund | April | $8,400.00 | JPM Checking (#1) | `tax_refund` | "CA Franchise Tax Board" |

Tag all rental income and rental property expenses to their respective `real_estate_property_id`.

Silver Lake Unit B — model as $0 in November 2024 (vacancy). All Silver Lake rental amounts tag to Property 2.

### Monthly Expense & Transfer Pattern

**Fixed monthly (checking debits — Account #1 unless noted):**

| Merchant | Category | Amount | Notes |
|---|---|---|---|
| JPM Chase Private Mortgage | `mortgage_payment` | $15,050.00 | Transfer to Account #17; jumbo 30yr at 3.875% |
| Wells Fargo | `mortgage_payment` | $5,170.00 | Transfer to Account #18; Silver Lake duplex mortgage — tag to Property 2 |
| LoanDepot | `mortgage_payment` | $4,876.00 | Transfer to Account #19; Palm Springs — tag to Property 3 |
| Chase HELOC | `heloc_payment` | $920.00 | Interest-only payment on $92K outstanding; transfer to Account #20 |
| Tesla Financial | `loan_payment` | $1,288.00 | Transfer to Account #21 (+ $500 extra = $1,788/mo total) |
| Porsche Financial | `loan_payment` | $752.00 | Transfer to Account #22 |
| Schwab Auto-Invest (joint) | `brokerage_contribution` | $5,000.00 | Transfer to Account #9 |
| Ben Fidelity Brokerage | `brokerage_contribution` | $2,000.00 | Transfer to Account #10; from Account #3 (Schwab Checking) |
| ScholarShare 529 | `brokerage_contribution` | $2,333.00 | Transfer to Account #12 (through July 2025, then $0) |
| CC Payment — Amex Platinum | `cc_payment` | (statement balance) | From Account #3 (Schwab Checking) |
| CC Payment — Amex Gold | `cc_payment` | (statement balance) | From Account #1 (JPM Checking) |
| CC Payment — Chase Sapphire | `cc_payment` | (statement balance) | From Account #1 |

**Variable monthly (high-income spending patterns; Amex Platinum unless noted):**

| Category | Merchant Examples | Monthly Range | Card |
|---|---|---|---|
| `groceries` | Erewhon, Bristol Farms, Gelson's, Costco | $1,800–$2,400 | Amex Gold (4x groceries) |
| `restaurants` | Nobu, Jon & Vinny's, Spago, local bistros | $1,400–$2,800 | Amex Platinum (5x dining) |
| `coffee` | Starbucks Reserve, Blue Bottle | $120–$180 | Amex Gold |
| `food_delivery` | Uber Eats, Postmates | $200–$350 | Amex Gold |
| `gas_fuel` | Chevron (Ben), (Gabriela — EV charging) | $95.00 (gas) | Chase Sapphire |
| `ev_charging` | Tesla Supercharger | $65–$120/mo | Amex Platinum |
| `internet` | Spectrum Business | $120.00 | Checking |
| `cell_phone` | AT&T (4 lines — Ben, Gabriela, Sophia, Ethan) | $320.00 | Amex Platinum |
| `streaming` | Netflix 4K, HBO Max, Apple TV+, Spotify, Peloton | $128.00 | Amex Platinum |
| `electric` | SCE (Brentwood) | $380.00 (summer: $520) | Checking |
| `water_sewer` | LADWP | $165.00 | Checking |
| `gas_heating` | SoCalGas | $85.00 (winter: $220) | Checking |
| `auto_insurance` | AIG Private Client (both cars) | $645.00 | Checking |
| `home_insurance` | Chubb Masterpiece | $520.00 | Checking |
| `cleaning_services` | Housekeeper (3×/week) | $1,800.00 | Checking |
| `lawn_garden` | Gardener (weekly) | $680.00 | Checking |
| `fitness` | Equinox (Ben + Gabriela) | $390.00 | Amex Platinum |
| `therapy` | Weekly sessions (Ben + Gabriela) | $880.00 | Amex Platinum |
| `clothing` | Nordstrom, Saks, local boutiques | $800–$2,200 | Amex Platinum |
| `personal_care` | Salon, spa, grooming | $600–$1,100 | Amex Gold |
| `home_goods` | RH (Restoration Hardware), etc. | $400–$2,000 | Amex Platinum (occasional) |
| `subscriptions` | Amex Centurion Lounge, WSJ, FT, NYT, LinkedIn | $180.00 | Amex Platinum |
| `life_insurance` | Pacific Life (term + universal) | $1,240.00 | Checking |
| `advisory_fees` | Schwab Private Client | $1,800.00 | Checking (quarterly: $5,400 in Jan, Apr, Jul, Oct) |
| `pet_care` | Vet, groomer (Labrador Retriever "Mango") | $180–$450 | Amex Gold |

**Rental property expenses for Silver Lake Duplex (Property 2):**

| Category | Merchant | Amount | Frequency |
|---|---|---|---|
| `rental_maintenance` | Various contractors | $400–$2,500 | 1–3/quarter; use $1,200/mo average across 30 months |
| `rental_insurance` | Farmers Landlord | $285.00 | Monthly |
| `rental_property_tax` | LA County Assessor | $10,500.00 | Twice/year (April and October) |

**Palm Springs property expenses (Property 3):**

| Category | Merchant | Amount | Frequency |
|---|---|---|---|
| `rental_maintenance` | Local Palm Springs contractors | $200–$800 | Monthly during rental season; $100–$300 off-season |
| `property_management` | Stay Duvet (STR mgmt 15%) | 15% of gross STR income | Monthly (proportional) |
| `rental_insurance` | Proper Insurance (STR policy) | $320.00 | Monthly |
| `rental_property_tax` | Riverside County | $5,800.00 | Twice/year (March and November) |

**Seasonal / annual:**

| Month(s) | Category | Merchant | Amount |
|---|---|---|---|
| Jan | `travel` | Private charter or first-class flights | $8,000–$14,000 |
| June | — | (Palm Springs personal use month) | — |
| July | `travel` | European vacation (flights + hotels) | $18,000–$28,000 |
| September | `tuition` | UCSB fall quarter fees (Ethan) | $4,800 |
| December | `tuition` | UCSB winter quarter (Ethan) | $4,800 |
| March | `tuition` | UCSB spring quarter (Ethan) | $4,800 |
| December | `gifts_given` | Amazon, high-end retail | $5,000–$8,000 |
| April | `tax_prep` | Holthouse Carlin & Van Trigt LLP (CPA) | $12,500 |
| February | `professional_services` | Estate attorney annual review | $4,200 |
| August | `home_maintenance` | Major pool service + HVAC service | $3,500–$6,000 |

**Sophia's own income** (she has the `dependent` role, earns ~$62K/year at a streaming company): Do NOT create a salary deposit from her employer to any HearthLedger account — she manages her own personal accounts externally. The only HearthLedger transaction related to Sophia is the monthly $500 deposit from Ben into her Roth IRA (Account #11), which originates from Account #1 and is tagged as `ira_contribution` / `gifts_given`. This shows the system correctly handling a grant for a dependent's individual account visible only to primary.

### Budget Configuration (effective 2024-01-01)

| Category | Monthly Budget |
|---|---|
| `groceries` | 2,000.00 |
| `restaurants` | 2,000.00 |
| `coffee` | 150.00 |
| `food_delivery` | 300.00 |
| `gas_fuel` | 120.00 |
| `ev_charging` | 100.00 |
| `internet` | 120.00 |
| `cell_phone` | 320.00 |
| `streaming` | 128.00 |
| `electric` | 420.00 |
| `fitness` | 390.00 |
| `therapy` | 880.00 |
| `cleaning_services` | 1,800.00 |
| `lawn_garden` | 680.00 |
| `clothing` | 1,500.00 |
| `personal_care` | 850.00 |
| `life_insurance` | 1,240.00 |
| `advisory_fees` | 1,800.00 |
| `travel` | 3,000.00 |
| `home_maintenance` | 800.00 |
| `pet_care` | 300.00 |
| `tuition` | 1,600.00 |

Add a budget update for `restaurants` effective `2025-06-01`: amount `2,400.00` (intentional lifestyle increase after Sophia lands on her feet). This exercises budget history alongside H2.

---

## 7. Seed Script Implementation Notes

### Transaction generation algorithm

```python
def generate_transactions(
    account_map: dict,
    category_map: dict,
    property_map: dict,
    monthly_pattern: list[TransactionSpec],
    date_range: tuple[date, date],
    rng: random.Random,
) -> list[TransactionRow]:
    ...
```

For each month in the date range:
1. Generate all fixed transactions first (exact amounts, exact dates as specified).
2. For each variable category, pick a random total amount within the specified range.
3. Split that total into N transactions where N is sampled from the specified frequency range, spread across plausible weekdays (avoid Sundays for grocery shops, prefer Fridays for restaurants, etc.).
4. For merchant names, use the provided merchant examples — pick one per transaction from the list. For recurring fixed payments, use the exact merchant name every time (so the system's future import-deduplication logic has something consistent to work with).
5. Set `is_cleared = True` for all transactions dated before June 1, 2026. Set `is_cleared = False` for June 2026 transactions.
6. Set `is_transfer = True` for all transfer-type transactions. Set `category_id` to the relevant transfer category slug.
7. For rental income and rental expense transactions, set `real_estate_property_id` to the corresponding property's UUID.
8. Transfer transactions that move money between two HearthLedger accounts (e.g., checking → credit card payment) must create TWO transaction rows: a debit on the source account and a credit on the destination account, both with `is_transfer = True` and the same `memo` (e.g., "Chase Sapphire Statement Payment").

### Amount sign convention

Confirm this against the actual model, but the expected convention is:

- **Asset accounts (checking, savings, brokerage, etc.):** Deposits are **positive**, withdrawals are **negative**.
- **Liability accounts (credit card, mortgage, loan):** Charges are **negative** (increasing the balance owed), payments are **positive** (reducing the balance owed).

### Balance snapshot generation

For each investment/retirement/HSA account, generate one balance snapshot per month (on the last calendar day of the month) from January 31, 2024 through May 31, 2026. The June 2026 current balance is stored in the `accounts.current_balance` column, not as a snapshot.

### Data integrity checks to run at end of script

After all inserts complete, the script should query and print:

```
=== HearthLedger Demo Data Summary ===

Household 1: Chen-Nakamura (Austin TX)
  Members: 2 | Accounts: 12 | Transactions: ~XXXX | Properties: 1
  Computed Net Worth: $XXX,XXX
  FIRE scenarios: 1 | Debt scenarios: 1

Household 2: Okonkwo-Rivera (Naperville IL)
  Members: 4 | Accounts: 19 | Transactions: ~XXXX | Properties: 2
  Computed Net Worth: $X,XXX,XXX
  FIRE scenarios: 2 | Debt scenarios: 2

Household 3: Whitfield-Torres (Brentwood LA)
  Members: 4 | Accounts: 25 | Transactions: ~XXXX | Properties: 3
  Computed Net Worth: $X,XXX,XXX
  FIRE scenarios: 2 | Debt scenarios: 1

Total transactions generated: ~XXXX
Run time: Xs
```

Computed net worth = sum of all account `current_balance` values (which are positive for assets, negative for liabilities).

### Reference demographic calibration

These households were designed against the following benchmarks:

| Household | Target NW | SCF Percentile (2022 data) | Age Cohort Benchmark |
|---|---|---|---|
| Chen-Nakamura | ~$899K | ~Top 12% (ages 35–44, threshold ≈ $1.04M for top 10%) | Solidly upper-middle class |
| Okonkwo-Rivera | ~$3.4M | ~Top 4–5% nationally | Very affluent, professional household |
| Whitfield-Torres | ~$9.5M | ~Top 1.5–2% (top 1% threshold was ~$13.7M in 2023 SCF) | High-net-worth |

Home values reflect: Round Rock TX ~$665K median (post-2021 cooling); Naperville IL ~$1.2M for 4BR+ executive-tier; Brentwood LA ~$4.1M (consistent with December 2025 LA City median of $1.15M; Brentwood is 2.5–4× the city median). Tax rates use 2025 brackets: federal MFJ (10%–37%), California progressive up to 13.3%, Illinois flat 4.95%, Texas 0%.

---

*End of HearthLedger Demo Dataset Specification*
