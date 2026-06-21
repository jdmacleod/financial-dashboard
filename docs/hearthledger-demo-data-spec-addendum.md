# HearthLedger — Demo Dataset Specification: Addendum

## Households 4 & 5

**Companion to:** `hearthledger-demo-data-spec.md` (Households 1–3)
**Transaction date range:** January 1, 2024 – June 20, 2026 (same 30-month window)
**Seed script entry:** Same `seed_demo_data.py` with `--household 4`, `--household 5`, or `--household all`

---

## A. Taxonomy Additions

The following categories supplement the shared taxonomy defined in the original spec. They are required for H4 and H5 and should be created per-household alongside all existing categories. Apply the same `is_system = True` flag.

### Additional income categories

| Slug                     | Name                    | Parent              | Notes                                             |
| ------------------------ | ----------------------- | ------------------- | ------------------------------------------------- |
| `social_security_income` | Social Security Benefit | `other_income`      | H5: active monthly income from SSA                |
| `pension_income`         | Pension Benefit         | `other_income`      | H5: monthly defined-benefit pension check         |
| `rmd_distribution`       | IRA Distribution / RMD  | `investment_income` | H5: quarterly RMD withdrawal credited to checking |

### Additional expense categories

| Slug                 | Name                    | Parent       | Notes                                           |
| -------------------- | ----------------------- | ------------ | ----------------------------------------------- |
| `rent`               | Rent                    | `housing`    | H4: primary housing expense                     |
| `renters_insurance`  | Renter's Insurance      | `housing`    | H4                                              |
| `medicare_part_b`    | Medicare Part B Premium | `healthcare` | H5: Bob's monthly Part B + IRMAA surcharge      |
| `medicare_part_d`    | Medicare Part D Premium | `healthcare` | H5: Bob's monthly drug coverage                 |
| `medigap_supplement` | Medigap Supplement      | `healthcare` | H5: Bob's Plan G supplement                     |
| `aca_premium`        | ACA Marketplace Premium | `healthcare` | H5: Maggie's pre-Medicare coverage until age 65 |

---

## B. Household 4 — Park-Cole

### Overview

**Demographic context:** A recently married couple in their late 20s living in East Nashville, Tennessee — one of the most popular neighborhoods for young professionals in the Sun Belt. Zoe is a product designer at an early-stage SaaS startup; Marcus is a healthcare data analyst at HCA Healthcare (one of Nashville's largest employers, headquartered downtown). Tennessee has no state income tax, giving their take-home a slight edge over peers in income-tax states. They are renters saving aggressively for a home purchase — their "House Fund" brokerage is a named goal, not a general investment account. Both carry student loan debt, and Marcus also has an auto loan. They are disciplined, budget-conscious, and aware of their financial picture; they adopted HearthLedger specifically because spreadsheets weren't cutting it for multi-account debt payoff tracking and savings goal visualization.

This household exercises: renter (no real estate) net worth tracking, student loan + auto loan debt payoff projections (avalanche strategy across three simultaneous loans), a labeled savings-goal brokerage, early-stage retirement accumulation (Roth 401k vs. traditional 401k contrast), tight budget vs. actuals, and a long-horizon FIRE scenario.

**Net worth target:** ~$154,500
**Demographic benchmark:** Top 30–40% of US households under 35 by net worth (2022 SCF median for under-35 was ~$39K; this couple is well ahead due to high dual income and disciplined saving).

### Members

| Field           | Primary                | Partner                |
| --------------- | ---------------------- | ---------------------- |
| `display_name`  | Zoe Park               | Marcus Cole            |
| `email`         | zoe@park-cole.local    | marcus@park-cole.local |
| `password_hash` | bcrypt("HearthDemo1!") | bcrypt("HearthDemo1!") |
| `role`          | `primary`              | `partner`              |
| `is_active`     | true                   | true                   |

### Accounts

| #   | Name                   | Institution                | Type              | Ownership  | Member | Last Four | Current Balance |
| --- | ---------------------- | -------------------------- | ----------------- | ---------- | ------ | --------- | --------------- |
| 1   | Joint Checking         | Ally Bank                  | `checking`        | joint      | null   | 4492      | 9,400.00        |
| 2   | Emergency Fund         | Ally Bank                  | `savings`         | joint      | null   | 5513      | 35,000.00       |
| 3   | House Fund             | Fidelity                   | `brokerage`       | joint      | null   | 6624      | 88,400.00       |
| 4   | Roth 401(k)            | Guideline                  | `retirement_401k` | individual | Zoe    | 7735      | 22,400.00       |
| 5   | 401(k)                 | Fidelity (HCA NetBenefits) | `retirement_401k` | individual | Marcus | 8846      | 46,800.00       |
| 6   | Roth IRA               | Fidelity                   | `retirement_ira`  | individual | Zoe    | 9957      | 12,200.00       |
| 7   | Roth IRA               | Vanguard                   | `retirement_ira`  | individual | Marcus | 1068      | 9,400.00        |
| 8   | HSA                    | HealthEquity               | `hsa`             | individual | Zoe    | 2179      | 5,200.00        |
| 9   | Freedom Unlimited      | Chase                      | `credit_card`     | joint      | null   | 3280      | -2,400.00       |
| 10  | Apple Card             | Goldman Sachs              | `credit_card`     | individual | Zoe    | 4381      | -1,100.00       |
| 11  | Federal Student Loan   | MOHELA                     | `loan`            | individual | Zoe    | 5492      | -34,000.00      |
| 12  | Federal Student Loan   | MOHELA                     | `loan`            | individual | Marcus | 6503      | -22,000.00      |
| 13  | Honda Accord Auto Loan | Tennessee CU               | `loan`            | individual | Marcus | 7614      | -14,800.00      |

No real estate accounts — this household rents.

**Net worth sanity check:**
Assets: 9,400 + 35,000 + 88,400 + 22,400 + 46,800 + 12,200 + 9,400 + 5,200 = **228,800**
Liabilities: 2,400 + 1,100 + 34,000 + 22,000 + 14,800 = **74,300**
**Net worth: $154,500** ✓

### Loan Details (for debt payoff calculations)

| Loan                | Member | Original Balance | Current Balance | APR   | Monthly Min | Loan Start |
| ------------------- | ------ | ---------------- | --------------- | ----- | ----------- | ---------- |
| Zoe Student Loan    | Zoe    | $42,000          | $34,000         | 5.50% | $275.00     | 2021-08    |
| Marcus Student Loan | Marcus | $28,000          | $22,000         | 4.80% | $182.00     | 2019-06    |
| Honda Accord Auto   | Marcus | $18,500          | $14,800         | 6.90% | $312.00     | 2022-03    |

**Avalanche priority order** (by APR, highest first):

1. Honda Accord (6.90%) — absorbs all extra payment until paid off
2. Zoe Student Loan (5.50%) — then absorbs full cascading extra + freed car payment
3. Marcus Student Loan (4.80%) — last to be eliminated

### Investment Account Balance Snapshots

Generate monthly snapshots (last day of each month) from January 2024 through May 2026. The current balance (June 2026) lives in `accounts.current_balance`.

| Account                   | Jan 2024 Balance | Monthly Contribution                     | Employer Match                 |
| ------------------------- | ---------------- | ---------------------------------------- | ------------------------------ |
| Zoe Roth 401(k)           | 14,200           | $390/mo (6% of $78K / 12)                | None (startup offers no match) |
| Marcus 401(k) Traditional | 32,400           | $440/mo (6% of $88K / 12)                | 4% match: $293/mo              |
| Zoe Roth IRA              | 7,800            | $583/mo Jan–Oct; $0 Nov–Dec              | —                              |
| Marcus Roth IRA           | 5,200            | $583/mo Jan–Oct; $0 Nov–Dec              | —                              |
| Zoe HSA                   | 2,200            | $358/mo (self-only HDHP max $4,300 / 12) | —                              |
| House Fund (brokerage)    | 42,000           | $2,000/mo (steady auto-invest)           | —                              |

Growth formula: `balance[m] = balance[m-1] × (1 + 0.085/12) + contribution[m]` (8.5% annual return for long-horizon growth accounts). Apply a -3.5% drawdown to all investment accounts in October 2024 to simulate a brief correction. The House Fund earns a more conservative 6.5% (shorter time horizon, more conservatively allocated: 60/40 stock-bond split) — use the formula `balance[m] = balance[m-1] × (1 + 0.065/12) + 2000`.

### Monthly Income Pattern

Both paid biweekly (26 pay periods per year). Model as two deposits per month; in the three months per year where a third paycheck occurs (for Zoe: March, August, and November 2024; for Marcus: January, June, and November 2024), add a third deposit of the same amount.

| Payer                   | Deposit Days | Net Per Paycheck | Account  | Category | Merchant                 |
| ----------------------- | ------------ | ---------------- | -------- | -------- | ------------------------ |
| DataOps (Zoe)           | 7th and 21st | $2,210.00        | Checking | `salary` | "DataOps Inc. Payroll"   |
| HCA Healthcare (Marcus) | 1st and 15th | $2,870.00        | Checking | `salary` | "HCA Healthcare Payroll" |

**Annual tax refund** (April, federal only — Tennessee has no state income tax):
$1,650 federal refund, merchant "IRS TREAS 310", category `tax_refund`, to Checking (Account #1).

**Combined net monthly household income:** ~$10,160/month (in standard two-paycheck months)

### Monthly Expense & Transfer Pattern

**Fixed monthly (checking direct debits):**

| Merchant                        | Category                 | Amount              | Notes                                                          |
| ------------------------------- | ------------------------ | ------------------- | -------------------------------------------------------------- |
| 4th Ave Partners (landlord)     | `rent`                   | $1,875.00           | 2BR apartment, East Nashville; direct debit 1st of month       |
| State Farm Renters              | `renters_insurance`      | $22.00              |                                                                |
| MOHELA (Zoe)                    | `loan_payment`           | $675.00             | Transfer to Account #11; min $275 + $400 extra (avalanche)     |
| MOHELA (Marcus)                 | `loan_payment`           | $182.00             | Transfer to Account #12; minimum only until auto loan paid off |
| Tennessee CU Auto               | `loan_payment`           | $812.00             | Transfer to Account #13; min $312 + $500 extra (avalanche)     |
| Fidelity House Fund             | `brokerage_contribution` | $2,000.00           | Transfer to Account #3 on 1st of month                         |
| Zoe Roth IRA (Jan–Oct)          | `ira_contribution`       | $700.00             | Transfer to Account #6                                         |
| Marcus Roth IRA (Jan–Oct)       | `ira_contribution`       | $700.00             | Transfer to Account #7                                         |
| Zoe 401k (payroll deduction)    | —                        | —                   | Pre-tax payroll; not a checking transaction                    |
| Marcus 401k (payroll deduction) | —                        | —                   | Pre-tax payroll; not a checking transaction                    |
| CC Payment — Chase Freedom      | `cc_payment`             | (statement balance) | Transfer Checking → Account #9                                 |
| CC Payment — Apple Card         | `cc_payment`             | (statement balance) | Transfer Checking → Account #10                                |

**Note on auto loan payoff event:** The Honda Accord loan (Account #13) at $14,800 current balance and $812/month total payment will be paid off approximately 20–21 months into the seed data window (around August–September 2025). After payoff: the $500 extra payment from the auto loan cascades to the Zoe Student Loan. Update MOHELA (Zoe) payment to $775/month starting October 2025 (min $275 + cascaded $500) and auto loan shows $0 balance. The Honda loan account should remain `is_active = false` with $0 balance. Generate a zero-balance snapshot for Account #13 from October 2025 onward; no further `loan_payment` transactions to Account #13 after payoff month.

**Variable monthly (split between Chase Freedom Unlimited and Apple Card):**

| Category          | Merchant Examples                                                 | Monthly Range | Card                                                     |
| ----------------- | ----------------------------------------------------------------- | ------------- | -------------------------------------------------------- |
| `groceries`       | Kroger, Whole Foods, Trader Joe's, Costco                         | $480–$580     | Chase Freedom (5% on groceries rotating)                 |
| `restaurants`     | Butcher & Bee, Biscuit Love, Rolf & Daughters, local brunch spots | $260–$380     | Chase Freedom                                            |
| `coffee`          | Frothy Monkey, Steadfast Coffee, Crema                            | $55–$80       | Apple Card                                               |
| `food_delivery`   | DoorDash, Uber Eats                                               | $40–$85       | Chase Freedom                                            |
| `gas_fuel`        | Circle K, Mapco                                                   | $95–$145      | Chase Freedom (5% rotating)                              |
| `internet`        | Comcast Xfinity                                                   | $68.00        | Checking (direct debit)                                  |
| `cell_phone`      | T-Mobile (2 lines)                                                | $95.00        | Chase Freedom                                            |
| `streaming`       | Netflix, Hulu, Spotify                                            | $42.00        | Apple Card                                               |
| `auto_insurance`  | Progressive (1 car, Marcus)                                       | $124.00       | Checking                                                 |
| `fitness`         | Planet Fitness (Marcus), ClassPass (Zoe)                          | $58.00        | Chase Freedom                                            |
| `clothing`        | Target, Shein, ThredUp, ASOS                                      | $65–$150      | Apple Card                                               |
| `personal_care`   | Ulta, pharmacy, barbershop                                        | $55–$100      | Apple Card                                               |
| `electronics`     | Amazon, Best Buy                                                  | $0–$200       | Apple Card (occasional; skip most months)                |
| `subscriptions`   | Amazon Prime, NYT, Xbox GamePass                                  | $32.00        | Chase Freedom                                            |
| `events_tickets`  | Ryman Auditorium, Bridgestone Arena, Broadway honky-tonks         | $60–$180      | Chase Freedom                                            |
| `hobbies`         | Disc golf, hiking gear, thrift finds                              | $30–$90       | Apple Card                                               |
| `pharmacy`        | Walgreens, CVS                                                    | $20–$55       | Apple Card                                               |
| `car_maintenance` | Jiffy Lube, Midas                                                 | $0–$220       | Chase Freedom (quarterly oil change + occasional repair) |

**Seasonal / annual:**

| Month(s) | Category      | Merchant                                                 | Amount      |
| -------- | ------------- | -------------------------------------------------------- | ----------- |
| February | `travel`      | Airbnb + drive trip (e.g., Gatlinburg, Chattanooga)      | $350–$600   |
| June     | `travel`      | Flight + hotel (visit Zoe's family in Phoenix, AZ)       | $900–$1,400 |
| October  | `travel`      | Road trip (New Orleans or Atlanta)                       | $550–$850   |
| December | `gifts_given` | Amazon, local Nashville shops                            | $400–$700   |
| April    | `tax_prep`    | TurboTax                                                 | $65.00      |
| August   | `electronics` | (Marcus: one significant purchase, e.g., laptop upgrade) | $800–$1,200 |
| January  | `home_goods`  | IKEA, Target (apartment refresh)                         | $150–$350   |

**Debt payoff milestone notes for transaction generation:**

- Months 1–20 (Jan 2024 – Aug 2025): Auto loan active at $812/mo; Zoe student loan at $675/mo; Marcus student loan at $182/mo.
- Month 21 (Sept 2025): Auto loan final payment (partial month to bring to zero). Generate a `loan_payment` for the exact remaining balance ($14,800 minus ~20 × $812 reduction). Flag account as paid off.
- Months 22–30 (Oct 2025 – Jun 2026): Auto loan gone. Zoe student loan jumps to $775/mo. Marcus student loan remains at $182/mo.
- No cascading to Marcus student loan will occur within the 30-month data window — that happens after Zoe's loan is cleared (~36+ more months).

### FIRE Scenario

| Field                    | Value                          |
| ------------------------ | ------------------------------ |
| `name`                   | "Financial Independence by 45" |
| `member_id`              | Zoe (primary)                  |
| `target_retirement_age`  | 45                             |
| `expected_return_annual` | 0.0750                         |
| `inflation_rate_annual`  | 0.0300                         |
| `target_annual_spend`    | 120,000.0000                   |

`additional_income_streams` JSONB:

```json
[
  {
    "id": "<uuid>",
    "label": "Zoe — Product Designer",
    "type": "salary",
    "amount_annual": 78000.0,
    "start_year": 2024,
    "end_year": 2044,
    "growth_rate_annual": 0.04
  },
  {
    "id": "<uuid>",
    "label": "Marcus — HCA Healthcare",
    "type": "salary",
    "amount_annual": 88000.0,
    "start_year": 2024,
    "end_year": 2042,
    "growth_rate_annual": 0.035
  },
  {
    "id": "<uuid>",
    "label": "Zoe Social Security (age 67)",
    "type": "social_security",
    "amount_annual": 34000.0,
    "start_year": 2064,
    "end_year": null,
    "growth_rate_annual": 0.025
  },
  {
    "id": "<uuid>",
    "label": "Marcus Social Security (age 67)",
    "type": "social_security",
    "amount_annual": 38000.0,
    "start_year": 2064,
    "end_year": null,
    "growth_rate_annual": 0.025
  }
]
```

This scenario is aspirational — at current savings rates it likely falls short of the 45 target, which is intentional: it creates an informative gap between projected FI date and the stated goal, demonstrating the FIRE modeling feature's motivational value.

### Debt Payoff Scenarios

Create three rows, all using `avalanche` strategy. The script should note that avalanche applies them in APR order; each row records just the extra payment committed to that account, not the cascading total.

| Account                           | Strategy    | Extra Monthly Payment               |
| --------------------------------- | ----------- | ----------------------------------- |
| Honda Accord Auto (Account #13)   | `avalanche` | 500.00                              |
| Zoe Student Loan (Account #11)    | `avalanche` | 400.00                              |
| Marcus Student Loan (Account #12) | `avalanche` | 0.00 (no extra yet; awaits cascade) |

### Budget Configuration (effective 2024-01-01)

| Category            | Monthly Budget |
| ------------------- | -------------- |
| `rent`              | 1,875.00       |
| `renters_insurance` | 22.00          |
| `groceries`         | 520.00         |
| `restaurants`       | 300.00         |
| `coffee`            | 65.00          |
| `food_delivery`     | 60.00          |
| `gas_fuel`          | 120.00         |
| `internet`          | 68.00          |
| `cell_phone`        | 95.00          |
| `streaming`         | 42.00          |
| `auto_insurance`    | 124.00         |
| `fitness`           | 58.00          |
| `clothing`          | 90.00          |
| `personal_care`     | 75.00          |
| `subscriptions`     | 32.00          |
| `events_tickets`    | 100.00         |
| `pharmacy`          | 40.00          |
| `travel`            | 150.00         |
| `gifts_given`       | 60.00          |

Add a budget revision for `restaurants` effective `2025-01-01`: amount `340.00` (intentional lifestyle creep after Marcus gets a raise — exercises budget history alongside H2 and H3, giving three households with budget history data).

Add a budget revision for `groceries` effective `2025-06-01`: amount `560.00` (food inflation).

---

## C. Household 5 — Langford

### Overview

**Demographic context:** A dual-generation retirement-transition household in Sarasota, Florida. Robert ("Bob") Langford, 74, is a fully retired former CFO who spent 28 years as finance chief at Meridian Packaging Corporation (a mid-size Cincinnati-based industrial firm). He retired at 70, delayed Social Security to the maximum age for the highest benefit, and just entered his first year of Required Minimum Distributions in 2025 — a pivotal financial event that this dataset captures in real time. Margaret ("Maggie") Langford, 63, left her corporate HR Director role at 61 and now runs a boutique HR consulting practice, Langford HR Consulting LLC, at roughly 15 hours per week. She is deferring Social Security to her Full Retirement Age (67, in 2029) or beyond, to maximize the benefit. She will begin receiving a small former-employer pension at 65 (2027, just outside the data window). She is on an ACA Marketplace plan and will transition to Medicare in 2027. Florida has no state income tax — relevant since SS, pension, and RMD income are free of state tax.

This household uniquely exercises: Social Security as active monthly income (not a future FIRE stream), pension income as active income, RMDs (absent in 2024, present starting in 2025 — a meaningful before/after pattern in the transaction history), Medicare IRMAA surcharges (Bob) vs. ACA Marketplace premium (Maggie), two-property real estate with a small vacation-home mortgage, large investment portfolio with taxable brokerage dividend income, a FIRE scenario functioning as a 30-year sustainability check rather than an accumulation target, and the complexity of income layering from six distinct sources.

**Net worth target:** ~$12,856,700
**Demographic benchmark:** Top 1.5–2% of US household wealth (2022 SCF top-1% threshold was ~$13.7M; this household is just below that threshold, in the 98th–99th percentile range).

### Members

| Field           | Primary                | Partner                |
| --------------- | ---------------------- | ---------------------- |
| `display_name`  | Robert Langford        | Margaret Langford      |
| `email`         | bob@langford.local     | maggie@langford.local  |
| `password_hash` | bcrypt("HearthDemo1!") | bcrypt("HearthDemo1!") |
| `role`          | `primary`              | `partner`              |
| `is_active`     | true                   | true                   |

No dependents. Two adult children live independently and are not household members.

### Accounts

| #   | Name                       | Institution          | Type             | Ownership  | Member | Last Four | Current Balance |
| --- | -------------------------- | -------------------- | ---------------- | ---------- | ------ | --------- | --------------- |
| 1   | Wealth Management Checking | Truist Bank Private  | `checking`       | joint      | null   | 8847      | 62,000.00       |
| 2   | Premium Savings            | Truist Bank Private  | `savings`        | joint      | null   | 9958      | 128,000.00      |
| 3   | Money Market (SWVXX)       | Schwab               | `savings`        | joint      | null   | 1069      | 265,000.00      |
| 4   | Consulting LLC Checking    | Regions Bank         | `checking`       | individual | Maggie | 2170      | 38,500.00       |
| 5   | Rollover IRA               | Schwab               | `retirement_ira` | individual | Bob    | 3281      | 3,850,000.00    |
| 6   | Rollover IRA               | Schwab               | `retirement_ira` | individual | Maggie | 4392      | 720,000.00      |
| 7   | Roth IRA                   | Fidelity             | `retirement_ira` | individual | Bob    | 5403      | 88,000.00       |
| 8   | Roth IRA                   | Vanguard             | `retirement_ira` | individual | Maggie | 6514      | 110,000.00      |
| 9   | Joint Taxable Brokerage    | Schwab               | `brokerage`      | joint      | null   | 7625      | 3,280,000.00    |
| 10  | Individual Brokerage       | Fidelity             | `brokerage`      | individual | Bob    | 8736      | 720,000.00      |
| 11  | Centurion Card             | American Express     | `credit_card`    | individual | Bob    | 9847      | -6,200.00       |
| 12  | Sapphire Reserve           | Chase                | `credit_card`    | joint      | null   | 1058      | -1,600.00       |
| 13  | Highlands NC Mortgage      | Bank of America      | `mortgage`       | joint      | null   | 2169      | -342,000.00     |
| 14  | Sarasota Primary Home      | (property valuation) | `real_estate`    | joint      | null   | —         | 2,850,000.00    |
| 15  | Highlands NC Vacation Home | (property valuation) | `real_estate`    | joint      | null   | —         | 1,095,000.00    |

**Net worth sanity check:**
Assets: 62,000 + 128,000 + 265,000 + 38,500 + 3,850,000 + 720,000 + 88,000 + 110,000 + 3,280,000 + 720,000 + 2,850,000 + 1,095,000 = **13,206,500**
Liabilities: 6,200 + 1,600 + 342,000 = **349,800**
**Net worth: $12,856,700** ✓

### Real Estate Properties

**Property 1 — Sarasota Primary Residence:**

| Field                 | Value                                       |
| --------------------- | ------------------------------------------- |
| `name` (encrypted)    | 4218 Bayside Terrace Court                  |
| `address` (encrypted) | 4218 Bayside Terrace Ct, Sarasota, FL 34231 |
| `property_type`       | `primary_residence`                         |
| `acquisition_date`    | 2022-03-18                                  |
| `acquisition_price`   | 2,100,000.0000                              |
| Member                | null (joint)                                |

Paid cash at purchase — no mortgage on this property. A bayfront-adjacent waterfront community west of Trail, single-family 4BR/3BA, private dock.

Annual Florida property expenses (outside seed transactions but budget-relevant): Homeowners insurance $9,200/year, flood insurance $5,400/year, wind/hurricane coverage $8,800/year (total ~$23,400/year = ~$1,950/month). Property tax at ~0.75% effective rate on $2.8M (post-homestead): ~$21,000/year, paid biannually in Florida (November and May).

Valuations:

| Date       | Amount       | Notes                          |
| ---------- | ------------ | ------------------------------ |
| 2024-01-01 | 2,580,000.00 | Strong post-pandemic FL market |
| 2024-07-01 | 2,650,000.00 |                                |
| 2025-01-01 | 2,720,000.00 | Moderate appreciation          |
| 2025-07-01 | 2,780,000.00 |                                |
| 2026-01-01 | 2,830,000.00 |                                |
| 2026-06-01 | 2,850,000.00 |                                |

**Property 2 — Highlands, NC Vacation Home:**

| Field                 | Value                                         |
| --------------------- | --------------------------------------------- |
| `name` (encrypted)    | 128 Ridgecrest Summit Drive                   |
| `address` (encrypted) | 128 Ridgecrest Summit Dr, Highlands, NC 28741 |
| `property_type`       | `vacation`                                    |
| `acquisition_date`    | 2019-06-04                                    |
| `acquisition_price`   | 720,000.0000                                  |
| Member                | null (joint)                                  |

They financed 52% at purchase ($375K loan, 30-year fixed at 3.25%). After 7 years, balance is $342,000. Monthly P&I payment: $1,632.

Highlands NC is a high-altitude (4,118 ft) resort community in the Nantahala National Forest — a popular second-home destination for affluent Florida and Southeast retirees. They typically spend May–September there to escape Florida summers.

Valuations:

| Date       | Amount       | Notes            |
| ---------- | ------------ | ---------------- |
| 2024-01-01 | 985,000.00   | Mountain NC boom |
| 2024-07-01 | 1,010,000.00 |                  |
| 2025-01-01 | 1,042,000.00 |                  |
| 2025-07-01 | 1,068,000.00 |                  |
| 2026-01-01 | 1,085,000.00 |                  |
| 2026-06-01 | 1,095,000.00 |                  |

### Investment Account Balance Snapshots

#### Bob's Rollover IRA (Account #5) — Critical RMD Transition

This account has a before/after structure that is the most important snapshot pattern in the entire five-household dataset. In 2024, Bob is 72 (born February 18, 1952); he turns 73 in February 2025. Under SECURE 2.0, his first RMD year is 2025. The snapshots must reflect:

- **2024 (Jan–Dec): No RMD withdrawals.** Steady growth only.
- **2025 (Jan–Dec): First RMD year.** Quarterly withdrawals based on December 31, 2024 balance ÷ 26.5 (Uniform Lifetime Table, age 73).
- **2026 (Jan–Jun): Second RMD year.** Quarterly withdrawals based on December 31, 2025 balance ÷ 25.5 (age 74 factor).

Snapshot generation formula and values:

| Period                            | Starting Balance | RMD Factor    | Approximate Annual RMD | Growth Rate |
| --------------------------------- | ---------------- | ------------- | ---------------------- | ----------- |
| Jan 2024 start                    | $3,450,000       | —             | $0                     | 7%/year     |
| Dec 31, 2024 (basis for 2025 RMD) | ~$3,699,000      | 26.5 (age 73) | ~$139,585              | —           |
| Dec 31, 2025 (basis for 2026 RMD) | ~$3,726,000      | 25.5 (age 74) | ~$146,118              | —           |
| Jun 2026 (current)                | ~$3,850,000      | —             | —                      | —           |

**Quarterly RMD transactions** (generate for 2025 and 2026 only):

Bob takes RMDs quarterly. For the checking account, generate a credit transaction on the last business day of March, June, September, and December. Simultaneously, the IRA's monthly snapshot for those months reflects the withdrawal reduction.

2025 RMD schedule (total ~$139,585):

| Quarter            | RMD Amount | Checking Deposit Date | IRA Snapshot Reduction    |
| ------------------ | ---------- | --------------------- | ------------------------- |
| Q1 2025 (March 31) | $34,896    | March 31              | Applied in March snapshot |
| Q2 2025 (June 30)  | $34,896    | June 30               | Applied in June snapshot  |
| Q3 2025 (Sept 30)  | $34,896    | September 30          | Applied in Sept snapshot  |
| Q4 2025 (Dec 15)   | $34,897    | December 15           | Applied in Dec snapshot   |

2026 RMD schedule (total ~$146,118, partial year in data window):

| Quarter            | RMD Amount | Checking Deposit Date |
| ------------------ | ---------- | --------------------- |
| Q1 2026 (March 31) | $36,530    | March 31              |
| Q2 2026 (June 30)  | $36,530    | June 30               |

All RMD deposits to Truist Checking (Account #1), category `rmd_distribution`, merchant "Schwab IRA Distribution — RMD".

#### All investment accounts snapshot summary:

| Account                        | Jan 2024  | Monthly Contribution                                                                      | Notes                                          |
| ------------------------------ | --------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Bob Rollover IRA (#5)          | 3,450,000 | 0 (no contributions to rollover IRA)                                                      | RMDs reduce balance quarterly from 2025        |
| Maggie Rollover IRA (#6)       | 602,000   | 0                                                                                         | Growth only (can't contribute to rollover IRA) |
| Bob Roth IRA (#7)              | 72,000    | $583/mo Jan–Oct (backdoor Roth, $7K max)                                                  | Roth IRA exempt from RMDs; grows tax-free      |
| Maggie Roth IRA (#8)           | 88,000    | $583/mo Jan–Oct (backdoor Roth)                                                           | Same                                           |
| Joint Brokerage (#9)           | 2,780,000 | $2,000/mo (reinvested dividends are separate from quarterly dividend income transactions) | Apply -4% dip in Oct 2024; -2.5% in Apr 2025   |
| Bob Individual Brokerage (#10) | 612,000   | $1,000/mo                                                                                 | Apply same dips                                |

Growth rate for taxable brokerage: 6.5% annual (more conservative, accounts for taxes on dividends). Growth rate for IRAs: 7% annual.

Maggie's SEP-IRA was rolled over in 2023 when she left corporate employment; it is now the Maggie Rollover IRA (Account #6). She still makes annual SEP-IRA contributions for her LLC consulting income. These are modeled as external to HearthLedger (Schwab handles the contribution directly from consulting income), but the balance snapshot reflects them: add $58,000 to Maggie's Rollover IRA in January 2024 and $61,000 in January 2025 (25% of net self-employment income, capped at annual limit). Add this as a lump-sum adjustment to the January snapshots of those years.

### Medicare & Healthcare Expense Context

**Bob's Medicare (2024–2026):**
Bob is fully enrolled in Medicare Parts A, B, D, and a Medigap Plan G supplement from UnitedHealthcare. His IRMAA tier is determined by his MAGI two years prior. Since he had no RMDs in 2023 or 2024, his 2026 IRMAA is based on his 2024 income (SS + pension + brokerage dividends + Maggie consulting = approx. $234K MAGI), placing him in **IRMAA Tier 1 for 2026** ($218K–$274K MFJ bracket).

| Medicare component               | 2024–2025 Monthly | 2026 Monthly | Notes                                      |
| -------------------------------- | ----------------- | ------------ | ------------------------------------------ |
| Part A                           | $0                | $0           | Premium-free (40+ quarters worked)         |
| Part B (standard + IRMAA Tier 1) | ~$280             | $284.10      | 2026 rate from CMS; 2024-25 slightly lower |
| Part D (standard + IRMAA Tier 1) | ~$48              | $49.00       | Drug plan + surcharge                      |
| Medigap Plan G                   | $192              | $198         | FL; age 74; modest annual increase         |
| **Total Bob Medicare**           | **~$520/mo**      | **~$531/mo** |                                            |

**Important planning note for FIRE scenario annotation:** Bob's 2025 income includes ~$139,585 in RMDs, pushing his estimated 2025 MAGI to approximately $396,000. This will push his 2027 IRMAA into **Tier 3** ($342K–$410K MFJ bracket), causing his 2027 Part B premium to jump to approximately $528/month per person. This is a real-world IRMAA "spike" from RMDs — note it explicitly in the FIRE scenario `additional_income_streams` memo field if the schema supports it.

Bob's Medicare premiums are auto-deducted from his Social Security check before deposit. The net SS deposit to checking is therefore: $5,417/month gross SS benefit minus ~$531/month in Medicare deductions = **~$4,886/month net SS deposit**. Model this correctly: generate the SS income transaction for the net amount ($4,886) and record the Medicare expenses as separate monthly expense transactions (see income pattern below).

**Maggie's ACA Marketplace (2024–2026):**
Maggie turns 65 in September 2027, which is outside the data window. Through June 2026 she remains on a Blue Cross Blue Shield Silver plan for the FL Marketplace. At their household income, no ACA subsidy applies.

| Year | Monthly ACA Premium | Notes                                 |
| ---- | ------------------- | ------------------------------------- |
| 2024 | $1,165.00           | BCBS Silver, age 62                   |
| 2025 | $1,245.00           | Age 63 (premiums increase with age)   |
| 2026 | $1,310.00           | Age 63–64 (partial year through June) |

Generate monthly `aca_premium` transactions from Truist Checking (Account #1), merchant "BCBS Blue Shield FL Marketplace".

### Monthly Income Pattern

All to Truist Checking (Account #1) unless noted.

| Source                      | Deposit Date                           | Net Amount                            | Category                 | Merchant                        | Notes                                                                                                         |
| --------------------------- | -------------------------------------- | ------------------------------------- | ------------------------ | ------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Social Security (Bob)       | 3rd Wednesday of month                 | $4,886.00                             | `social_security_income` | "US Treasury Social Security"   | Net of Medicare deductions ($531/mo). Gross SS $65,004/yr ÷ 12 = $5,417; minus Medicare auto-deduction ~$531. |
| Meridian Pension (Bob)      | 1st of month                           | $4,000.00                             | `pension_income`         | "Meridian Packaging Pension"    | DB plan, fixed $48K/year, paid via former employer trust                                                      |
| Bob IRA RMD (2025 only)     | See quarterly schedule above           | $34,896–$36,530                       | `rmd_distribution`       | "Schwab IRA Distribution — RMD" | 0 in 2024; quarterly starting Q1 2025                                                                         |
| Maggie Consulting LLC       | 15th of month (net, from LLC checking) | $3,200.00 avg                         | `consulting_fees`        | "Langford HR Consulting LLC"    | Transfer from Account #4 (LLC Checking) to Account #1; see LLC income/expense section below                   |
| Brokerage dividends — Joint | Last day of Mar, Jun, Sep, Dec         | $18,500 / $19,200 / $20,100 / $21,000 | `dividends`              | "Schwab Brokerage Dividend"     | Quarterly, reinvest choice OFF; deposits to Account #1                                                        |
| Brokerage dividends — Bob   | Last day of Mar, Jun, Sep, Dec         | $4,200 each quarter                   | `dividends`              | "Fidelity Brokerage Dividend"   | Deposits to Account #1                                                                                        |
| Florida tax refund          | N/A                                    | $0                                    | —                        | —                               | FL has no state income tax                                                                                    |
| Federal tax refund          | April                                  | $0                                    | —                        | —                               | At this income level they typically owe; no refund modeled                                                    |

**Maggie's consulting LLC income** (Account #4 — Regions Consulting LLC Checking):

Maggie invoices 4–6 clients monthly. Payment arrives 30 days after invoice. Model monthly LLC income (credits to Account #4) with the following seasonal pattern:

| Month Pattern      | LLC Revenue   | LLC Expenses (from Account #4)             | Net Monthly Transfer to Joint Checking |
| ------------------ | ------------- | ------------------------------------------ | -------------------------------------- |
| Jan, Feb, Mar, Apr | $5,200–$6,800 | $1,400 (software, professional dev, phone) | $3,800–$5,400                          |
| May, Jun           | $3,500–$4,200 | $1,200                                     | $2,300–$3,000                          |
| Jul, Aug           | $2,200–$2,800 | $900 (lower in summer — she's in NC)       | $1,300–$1,900                          |
| Sep, Oct, Nov      | $4,500–$5,500 | $1,300                                     | $3,200–$4,200                          |
| Dec                | $2,800–$3,400 | $1,100                                     | $1,700–$2,300                          |

LLC expenses include: `professional_dev` (industry conferences), `office_supplies`, `marketing_software` (LinkedIn Premium, HR tools), `cell_phone` (business line). These are `business_expenses` subcategories in Account #4.

The monthly "net transfer" from LLC checking (Account #4) to joint checking (Account #1) appears as `between_accounts` transfer type on both accounts.

### Monthly Expense & Transfer Pattern

**Fixed monthly (from Truist Checking, Account #1):**

| Merchant                             | Category                                          | Amount              | Notes                                                                                                                                                                  |
| ------------------------------------ | ------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BofA Mortgage                        | `mortgage_payment`                                | $1,632.00           | Transfer to Account #13; P+I on NC vacation home at 3.25%                                                                                                              |
| BCBS FL Marketplace                  | `aca_premium`                                     | $1,165–$1,310       | See schedule above; Maggie's health insurance                                                                                                                          |
| UnitedHealthcare (Medigap G)         | `medigap_supplement`                              | $192–$198           | Bob's supplemental insurance                                                                                                                                           |
| Medicare Part D Plan                 | `medicare_part_d`                                 | $49.00              | Bob; paid directly to insurer (auto-deducted from SS above per SSA process; model as expense transaction here for clarity even though it's embedded in net SS deposit) |
| Sarasota homeowners insurance        | `home_insurance`                                  | $1,950.00           | $23,400/year for wind + flood + HO coverage on FL waterfront; monthly installments                                                                                     |
| Florida property taxes               | `rental_property_tax` (use `housing` parent slug) | $1,750.00           | $21,000/year; model as monthly accrual, then actual payment: $10,500 in November and $10,500 in May                                                                    |
| NC home mortgage taxes               | —                                                 | —                   | NC property taxes $3,800/year; twice yearly (June $1,900 and December $1,900) — direct from checking                                                                   |
| NC homeowners insurance              | `home_insurance`                                  | $195.00             |                                                                                                                                                                        |
| CC Payment — Amex Centurion          | `cc_payment`                                      | (statement balance) | Transfer Checking → Account #11                                                                                                                                        |
| CC Payment — Chase Sapphire Reserve  | `cc_payment`                                      | (statement balance) | Transfer Checking → Account #12                                                                                                                                        |
| Savings xfr (monthly)                | `savings_transfer`                                | $5,000.00           | Transfer Checking → Truist Savings (Account #2); building reserves for anticipated tax payments                                                                        |
| Schwab auto-invest (joint brokerage) | `brokerage_contribution`                          | $2,000.00           | Transfer Checking → Account #9                                                                                                                                         |

**Variable monthly (split between Amex Centurion and Chase Sapphire Reserve):**

| Category            | Merchant Examples                                                                 | Monthly Range                                         | Card                                                  |
| ------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------- |
| `groceries`         | Publix, Fresh Market, Costco, Whole Foods                                         | $1,200–$1,600                                         | Chase Sapphire                                        |
| `restaurants`       | Indigenous, Selva Grill, local Sarasota restaurants                               | $1,600–$2,800                                         | Amex Centurion (4x dining)                            |
| `coffee`            | Perq Coffee Bar, Starbucks                                                        | $90–$130                                              | Amex Centurion                                        |
| `food_delivery`     | Uber Eats                                                                         | $80–$150                                              | Chase Sapphire                                        |
| `gas_fuel`          | Chevron, Shell                                                                    | $95–$140                                              | Chase Sapphire                                        |
| `electric`          | Sarasota (FPL / TECO)                                                             | $280–$420 (seasonal)                                  | Truist Checking                                       |
| `water_sewer`       | Sarasota County Utilities                                                         | $120.00                                               | Truist Checking                                       |
| `internet`          | Xfinity Business                                                                  | $115.00                                               | Truist Checking                                       |
| `cell_phone`        | AT&T (2 lines)                                                                    | $220.00                                               | Amex Centurion                                        |
| `streaming`         | Netflix, Apple TV+, SiriusXM, Peacock                                             | $85.00                                                | Amex Centurion                                        |
| `fitness`           | Planet Beach (Bob), YMCA (Maggie), golf club fees                                 | $420.00                                               | Amex Centurion                                        |
| `doctor_medical`    | Sarasota Memorial outpatient, specialists                                         | $180–$450                                             | Chase Sapphire                                        |
| `dental`            | Dr. Williams Dental (Sarasota)                                                    | $0–$380                                               | Amex Centurion (skip most months; semi-annual visits) |
| `pharmacy`          | Walgreens, CVS, mail-order Rx (Bob)                                               | $120–$280                                             | Chase Sapphire                                        |
| `personal_care`     | Salon, spa, grooming                                                              | $350–$600                                             | Amex Centurion                                        |
| `clothing`          | Nordstrom, Saks Sarasota (at The Mall at University Town Center), local boutiques | $400–$900                                             | Amex Centurion                                        |
| `home_maintenance`  | Sarasota contractors, pool service ($280/mo), HVAC                                | $400–$1,800                                           | Truist Checking                                       |
| `cleaning_services` | Weekly housekeeper                                                                | $640.00                                               | Truist Checking                                       |
| `lawn_garden`       | Weekly landscaper                                                                 | $480.00                                               | Truist Checking                                       |
| `subscriptions`     | Amex Platinum (annual fee), WSJ, FT, golf magazine, Kindle Unlimited              | $140.00                                               | Amex Centurion                                        |
| `life_insurance`    | Prudential term + umbrella policy                                                 | $685.00                                               | Truist Checking                                       |
| `advisory_fees`     | Schwab Private Client (quarterly)                                                 | 0 in non-quarter months; $4,500 in Jan, Apr, Jul, Oct | Truist Checking                                       |
| `pet_care`          | Vet, groomer (Golden Retriever "Biscuit")                                         | $120–$340                                             | Chase Sapphire                                        |
| `events_tickets`    | Van Wezel Performing Arts, Asolo Theatre, golf tournaments                        | $200–$600                                             | Amex Centurion                                        |

**Seasonal / annual:**

| Month(s)      | Category                                                                                                      | Merchant                                                        | Amount          |
| ------------- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | --------------- |
| Jan, Feb, Mar | `travel`                                                                                                      | Sarasota high season (minimal travel — they're home here now)   | $0–$400         |
| April         | `tax_prep`                                                                                                    | Roedel Parsons (CPA; Cincinnati-based firm they retained)       | $8,800          |
| April or Oct  | `advisory_fees`                                                                                               | Estate attorney annual review (Sarasota firm)                   | $3,200          |
| May           | `travel`                                                                                                      | Drive/fly to Highlands NC (relocation for summer)               | $800–$1,400     |
| May–Sept      | Lifestyle primarily in NC. Sarasota fixed expenses continue. Florida utilities drop to $120/month while away. |                                                                 |                 |
| June (NC)     | `home_maintenance`                                                                                            | NC seasonal maintenance (deck, HVAC, well check)                | $1,800–$3,500   |
| July (NC)     | `travel`                                                                                                      | One international trip (May-Aug window; e.g., Italy, Spain)     | $12,000–$18,000 |
| September     | `travel`                                                                                                      | Drive back to Sarasota for winter season                        | $600–$900       |
| November      | `home_maintenance`                                                                                            | FL home hurricane/winter prep; pool resurface (every few years) | $800–$4,000     |
| December      | `gifts_given`                                                                                                 | Amazon, high-end retail, family holiday                         | $3,200–$5,500   |
| December      | `home_goods`                                                                                                  | Sarasota interior refresh (they redecorate periodically)        | $1,500–$4,000   |

**NC property tax** (Property 2, NC vacation home): $1,900 in June and $1,900 in December, paid from Truist Checking, category `rental_property_tax` (or create a specific housing subcategory for NC; either works).

### FIRE Scenarios

For a retired household, the "FIRE scenario" becomes a sustainability/longevity check rather than an accumulation calculator. Model Bob's current age as the `target_retirement_age` equivalent — the scenario measures whether the portfolio sustains spending until age 95 or beyond.

**Scenario A — "30-Year Sustainability Check"**

| Field                    | Value                              |
| ------------------------ | ---------------------------------- |
| `name`                   | "30-Year Portfolio Sustainability" |
| `member_id`              | Bob                                |
| `target_retirement_age`  | 95                                 |
| `expected_return_annual` | 0.0550                             |
| `inflation_rate_annual`  | 0.0300                             |
| `target_annual_spend`    | 280,000.0000                       |

`additional_income_streams` JSONB — represents income they are receiving NOW or will receive soon:

```json
[
  {
    "id": "<uuid>",
    "label": "Bob Social Security (max benefit, claimed at 70)",
    "type": "social_security",
    "amount_annual": 65004.0,
    "start_year": 2020,
    "end_year": null,
    "growth_rate_annual": 0.025
  },
  {
    "id": "<uuid>",
    "label": "Bob Meridian Pension (fixed benefit)",
    "type": "pension",
    "amount_annual": 48000.0,
    "start_year": 2020,
    "end_year": 2045,
    "growth_rate_annual": 0.0
  },
  {
    "id": "<uuid>",
    "label": "Maggie Consulting (winding down at 67)",
    "type": "consulting",
    "amount_annual": 48000.0,
    "start_year": 2024,
    "end_year": 2029,
    "growth_rate_annual": -0.05
  },
  {
    "id": "<uuid>",
    "label": "Maggie Former Employer Pension (starting 2027, age 65)",
    "type": "pension",
    "amount_annual": 28800.0,
    "start_year": 2027,
    "end_year": 2055,
    "growth_rate_annual": 0.0
  },
  {
    "id": "<uuid>",
    "label": "Maggie Social Security (delayed to FRA, age 67)",
    "type": "social_security",
    "amount_annual": 42000.0,
    "start_year": 2029,
    "end_year": null,
    "growth_rate_annual": 0.025
  },
  {
    "id": "<uuid>",
    "label": "Joint Brokerage Dividends",
    "type": "other",
    "amount_annual": 78000.0,
    "start_year": 2024,
    "end_year": null,
    "growth_rate_annual": 0.02
  }
]
```

**Scenario B — "Conservative Longevity Stress Test"**

| Field                    | Value                                |
| ------------------------ | ------------------------------------ |
| `name`                   | "Longevity Stress Test (to Age 100)" |
| `member_id`              | Bob                                  |
| `target_retirement_age`  | 100                                  |
| `expected_return_annual` | 0.0450                               |
| `inflation_rate_annual`  | 0.0350                               |
| `target_annual_spend`    | 320,000.0000                         |

Income streams: identical to Scenario A but with `growth_rate_annual` set to 0.015 for SS (lower COLA assumption) and pension end years shortened to 2042 and 2050 to model earlier death of benefit on the pessimistic side.

This second scenario provides a paired comparison in the FIRE modeling UI — a high-confidence scenario vs. a stress test — which is a compelling demo of the multi-scenario feature.

### Debt Payoff Scenario

Only one active debt (NC vacation home mortgage at 3.25%). At this income level they choose not to accelerate payoff — the rate is below their portfolio return expectation — but recording it documents the option.

| Account                     | Strategy    | Extra Monthly Payment | Notes                                                                        |
| --------------------------- | ----------- | --------------------- | ---------------------------------------------------------------------------- |
| Highlands NC Mortgage (#13) | `avalanche` | 0.00                  | Rate arbitrage decision: 3.25% < expected portfolio return; no extra payment |

### Budget Configuration (effective 2024-01-01)

| Category             | Monthly Budget |
| -------------------- | -------------- |
| `groceries`          | 1,400.00       |
| `restaurants`        | 2,200.00       |
| `coffee`             | 110.00         |
| `food_delivery`      | 120.00         |
| `gas_fuel`           | 120.00         |
| `electric`           | 350.00         |
| `water_sewer`        | 120.00         |
| `internet`           | 115.00         |
| `cell_phone`         | 220.00         |
| `streaming`          | 85.00          |
| `home_insurance`     | 2,145.00       |
| `home_maintenance`   | 1,000.00       |
| `cleaning_services`  | 640.00         |
| `lawn_garden`        | 480.00         |
| `fitness`            | 420.00         |
| `doctor_medical`     | 300.00         |
| `pharmacy`           | 200.00         |
| `aca_premium`        | 1,165.00       |
| `medigap_supplement` | 192.00         |
| `medicare_part_d`    | 49.00          |
| `personal_care`      | 480.00         |
| `clothing`           | 650.00         |
| `life_insurance`     | 685.00         |
| `advisory_fees`      | 1,500.00       |
| `travel`             | 2,000.00       |
| `events_tickets`     | 400.00         |
| `gifts_given`        | 400.00         |
| `subscriptions`      | 140.00         |

Add a budget update for `aca_premium` effective `2025-01-01`: amount `1,245.00` (age-based annual increase). Add another effective `2026-01-01`: amount `1,310.00`. This exercises the budget history feature with real actuarial logic (ACA premiums increase with age), giving a third household — alongside H2 restaurants and H4 restaurants/groceries — with multi-year budget history.

---

## D. Five-Household Portfolio Summary

When the seed script runs `--household all`, the final summary table should show all five:

```
=== HearthLedger Demo Data Summary ===

H1  Chen-Nakamura    Austin TX      Members: 2  Accounts: 12  Properties: 1  NW: ~$898,900
H2  Okonkwo-Rivera   Naperville IL  Members: 4  Accounts: 19  Properties: 2  NW: ~$3,407,800
H3  Whitfield-Torres Brentwood LA   Members: 4  Accounts: 25  Properties: 3  NW: ~$9,463,400
H4  Park-Cole        Nashville TN   Members: 2  Accounts: 13  Properties: 0  NW: ~$154,500
H5  Langford         Sarasota FL    Members: 2  Accounts: 15  Properties: 2  NW: ~$12,856,700

Five states, five distinct income structures, zero state income tax in TX, TN, FL.
Net worth range: $154,500 → $12,856,700 (83× spread).
Total accounts seeded: 84.
Total transactions (estimated): ~14,000–18,000 across 30 months.
```

## E. Cross-Household Feature Coverage Matrix

| Feature                  | H1   | H2       | H3  | H4   | H5         |
| ------------------------ | ---- | -------- | --- | ---- | ---------- |
| Two-member RBAC          | ✓    | ✓        | ✓   | ✓    | ✓          |
| Dependent members        | —    | ✓        | ✓   | —    | —          |
| `account_access_grants`  | —    | ✓        | ✓   | —    | —          |
| Real estate + valuations | ✓    | ✓        | ✓   | —    | ✓          |
| Rental property P&L      | —    | ✓        | ✓   | —    | —          |
| STR / vacation rental    | —    | —        | ✓   | —    | —          |
| Multiple properties      | —    | ✓        | ✓   | —    | ✓          |
| Renting (no property)    | —    | —        | —   | ✓    | —          |
| Student loans            | —    | —        | —   | ✓    | —          |
| Auto loan                | ✓    | ✓        | ✓   | ✓    | —          |
| HELOC                    | —    | —        | ✓   | —    | —          |
| Budget vs. actuals       | ✓    | ✓        | ✓   | ✓    | ✓          |
| Budget history (2+ rows) | ✓    | ✓        | ✓   | ✓    | ✓          |
| Debt payoff (avalanche)  | ✓    | ✓        | ✓   | ✓    | —          |
| Debt payoff (snowball)   | —    | —        | —   | —    | —          |
| FIRE scenario            | ✓    | ✓        | ✓   | ✓    | ✓          |
| Multi-scenario FIRE      | —    | ✓        | ✓   | —    | ✓          |
| Pension income stream    | —    | ✓ (FIRE) | —   | —    | ✓ (active) |
| Social Security income   | —    | —        | —   | —    | ✓ (active) |
| RMDs                     | —    | —        | —   | —    | ✓          |
| Medicare IRMAA           | —    | —        | —   | —    | ✓          |
| ACA Marketplace          | —    | —        | —   | —    | ✓          |
| SEP-IRA                  | —    | —        | ✓   | —    | —          |
| Roth 401(k)              | —    | —        | —   | ✓    | —          |
| Traditional 401(k)       | ✓    | ✓        | ✓   | ✓    | —          |
| 529 accounts             | —    | ✓        | ✓   | —    | —          |
| HSA                      | ✓    | ✓        | ✓   | ✓    | —          |
| Business income          | —    | —        | ✓   | —    | ✓          |
| LLC checking             | —    | —        | —   | —    | ✓          |
| No state income tax      | ✓ TX | —        | —   | ✓ TN | ✓ FL       |
| High-income (>$400K)     | —    | —        | ✓   | —    | —          |
| Retirement income phase  | —    | —        | —   | —    | ✓          |
| Savings goal brokerage   | —    | —        | —   | ✓    | —          |
| Loan payoff milestone    | —    | —        | —   | ✓    | —          |

---

_End of HearthLedger Demo Dataset Specification Addendum (Households 4 & 5)_
