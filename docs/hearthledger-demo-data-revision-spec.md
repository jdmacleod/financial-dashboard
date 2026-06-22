# HearthLedger — Demo Dataset Revision & Extension Spec

## Handoff Artifact for Claude Code (Households 1–6, schema additions, scope documentation)

**Date prepared:** June 21, 2026
**Companion to:** `hearthledger-demo-data-spec.md` (H1–H3) and `hearthledger-demo-data-spec-addendum.md` (H4–H5)
**Source review:** `hearthledger-demo-data-review.md` (coverage analysis for the ≤ $20M band)
**Reference spec:** `~/Documents/hearthledger-spec/` — read `CLAUDE.md` and `docs/data-model.md` before implementing anything in this document.
**Seed script entry point:** `backend/scripts/seed_demo_data.py` — this spec adds `--household 6` and revises the H1–H5 generators.
**Transaction date range:** unchanged — January 1, 2024 → June 20, 2026 (≈ 30 months).

---

## 0. Purpose and execution model

This document does three things. First, it adds the data-model structures the existing dataset cannot currently express (trusts and ownership entities, insurance policies, equity-compensation grants and vesting, cost-basis lots, capital commitments, and revolving credit lines). Second, it revises the five existing households to populate those structures and to carry the advisory notes surfaced in the review. Third, it specifies a sixth household — a single, widowed individual at roughly $18.3M net worth — that closes the $13M–$20M gap and exercises the estate-and-legacy planning surface that married couples under the new $30M federal exemption cannot demonstrate. It also instructs the creation of a scope-boundaries document so that the deliberate upper limit of the system is recorded for future contributors rather than read as an oversight.

Execute the phases in order. **Phase A (schema) must precede everything else**, because every later phase writes rows into the new tables. Run Alembic migrations and confirm acceptance criteria for Phase A before touching seed data. Phases C, D, and E can be implemented in any order once A and B are complete.

All existing hard rules from `CLAUDE.md` continue to apply without exception. In particular: every account-like query routes through `AccountRepository.get_visible(ctx)`; every mutation uses a service method decorated with `@audit`; the `audit_log` table retains only SELECT/INSERT grants for the application role; encrypted fields never appear in audit-log entries; no plaintext PII is stored; only port 80 is exposed. New tables introduced here must be wired into the same visibility, audit, and encryption machinery. Continue to use `uv`, async SQLAlchemy 2.x with `asyncpg`, Alembic for migrations, deterministic per-household RNG seeding, `Decimal` for all monetary values, and UUID primary keys.

---

## Phase A — Data-model additions

Seven structural additions. Each is described as the table(s) and columns to create plus the integration points with existing machinery. Where a new construct needs to participate in net-worth math, RBAC visibility, or the audit log, that is called out explicitly. Treat additions 1–4 as required (they unlock the estate, insurance, equity-compensation, and concentration pillars used by multiple households); additions 5–6 are required only for H3 and H6 but should still be migrated now; addition 7 (advisory notes) is required so the review's findings can be persisted as first-class data.

### A.1 Ownership entities (trusts and titling layer)

Create table `ownership_entity`:

| Column                         | Type                        | Notes                                                                                                                    |
| ------------------------------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `id`                           | UUID PK                     |                                                                                                                          |
| `household_id`                 | UUID FK → households        |                                                                                                                          |
| `entity_type`                  | enum                        | `revocable_trust`, `irrevocable_trust`, `ilit`, `crt_crat`, `crt_crut`, `clt`, `llc`, `custodial_utma`, `custodial_ugma` |
| `name`                         | encrypted text              | e.g., "Castellano Family Revocable Trust" — PII, encrypt                                                                 |
| `grantor_member_id`            | UUID FK → members, nullable |                                                                                                                          |
| `is_in_taxable_estate`         | bool                        | `false` for ILIT/CRT/irrevocable; `true` for revocable — drives estate-exposure reporting                                |
| `counts_in_personal_net_worth` | bool                        | `false` for ILIT/CRT/DAF-held assets; `true` for revocable-trust titling                                                 |
| `created_at`                   | timestamptz                 |                                                                                                                          |

Add a nullable `ownership_entity_id` FK to **both** `accounts` and `real_estate_properties`. When present, the asset is titled in that entity rather than owned individually/jointly. Net-worth and estate-exposure aggregations must respect `counts_in_personal_net_worth` and `is_in_taxable_estate` on the linked entity: a revocable living trust is a pure titling layer (still in net worth, still in the taxable estate), whereas assets titled in an ILIT or CRT are excluded from personal net worth and from the taxable-estate figure. Wire visibility through the existing `get_visible(ctx)` path so entity-titled accounts respect RBAC. Encrypt `name`.

### A.2 Insurance policies

Create table `insurance_policy`:

| Column                      | Type                                 | Notes                                                                                                      |
| --------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| `id`                        | UUID PK                              |                                                                                                            |
| `household_id`              | UUID FK                              |                                                                                                            |
| `policy_type`               | enum                                 | `term_life`, `permanent_life`, `umbrella_liability`, `disability`, `long_term_care`, `scheduled_specialty` |
| `insured_member_id`         | UUID FK → members, nullable          |                                                                                                            |
| `owner_ownership_entity_id` | UUID FK → ownership_entity, nullable | non-null when an ILIT owns the policy                                                                      |
| `coverage_amount`           | Decimal                              | death benefit / liability limit / scheduled value                                                          |
| `premium_amount`            | Decimal                              | per the premium cadence                                                                                    |
| `premium_cadence`           | enum                                 | `monthly`, `quarterly`, `annual`                                                                           |
| `cash_value_account_id`     | UUID FK → accounts, nullable         | links a permanent policy to an asset account holding its cash value                                        |
| `metadata`                  | JSONB                                | scheduled-item list, riders, elimination period, etc.                                                      |

Permanent (cash-value) policies link to an `accounts` row of a new `account_type = 'life_insurance_cash_value'`, so the growing cash value flows through existing valuation and net-worth logic. Term/umbrella/DI/LTC/specialty policies carry no linked account; they contribute only a recurring premium expense and coverage metadata. Critically: if a permanent policy is **owned by an ILIT** (`owner_ownership_entity_id` set, entity `counts_in_personal_net_worth = false`), its cash value must **not** be counted in personal net worth — the policyholder funds it via gift transactions instead (see A.7 advisory note and H6).

### A.3 Equity-compensation grants and vesting

Create table `equity_grant`:

| Column                                | Type                     | Notes                                                        |
| ------------------------------------- | ------------------------ | ------------------------------------------------------------ |
| `id`                                  | UUID PK                  |                                                              |
| `household_id` / `member_id`          | UUID FKs                 |                                                              |
| `grant_type`                          | enum                     | `rsu`, `iso`, `nso`, `espp`                                  |
| `grant_date`                          | date                     |                                                              |
| `shares_granted`                      | Decimal                  |                                                              |
| `strike_price`                        | Decimal, nullable        | null for RSU                                                 |
| `ticker`                              | text                     | the employer security                                        |
| `vesting_schedule`                    | JSONB                    | cliff + cadence (e.g., 1-yr cliff then quarterly over 4 yrs) |
| `espp_discount_pct` / `espp_lookback` | Decimal / bool, nullable | ESPP only                                                    |

Create table `vesting_event`:

| Column                    | Type                               | Notes                                                |
| ------------------------- | ---------------------------------- | ---------------------------------------------------- |
| `id`                      | UUID PK                            |                                                      |
| `equity_grant_id`         | UUID FK                            |                                                      |
| `event_date`              | date                               |                                                      |
| `shares_vested`           | Decimal                            |                                                      |
| `fmv_at_event`            | Decimal                            |                                                      |
| `taxable_ordinary_income` | Decimal                            | RSU vest / NSO exercise / ESPP disqualifying portion |
| `amt_preference_amount`   | Decimal, nullable                  | ISO bargain element when exercised-and-held          |
| `shares_sold_to_cover`    | Decimal                            | sell-to-cover withholding                            |
| `resulting_lot_id`        | UUID FK → investment_lot, nullable | the lot created by retained shares                   |

A vesting event posts an income transaction (categorized `rsu_vest_income` / `nso_exercise_income` / `espp_purchase`), a sell-to-cover transfer, and creates an `investment_lot` (A.4) for retained shares. ISO exercises that are held set `amt_preference_amount` and create an advisory note about the AMT year. Because v1 defers gross-salary/payroll-deduction tracking, model the vest at **net** values and tag the withholding nuance as a v2 enrichment — do not block on it.

### A.4 Cost-basis lots

Create table `investment_lot`:

| Column            | Type               | Notes                                                                                       |
| ----------------- | ------------------ | ------------------------------------------------------------------------------------------- |
| `id`              | UUID PK            |                                                                                             |
| `account_id`      | UUID FK → accounts |                                                                                             |
| `ticker`          | text               |                                                                                             |
| `shares`          | Decimal            |                                                                                             |
| `basis_per_share` | Decimal            |                                                                                             |
| `acquired_date`   | date               |                                                                                             |
| `basis_type`      | enum               | `purchase`, `rsu_vest`, `espp`, `inherited_stepup`, `gift_carryover`, `reinvested_dividend` |

Lot-level basis is the prerequisite for concentration reporting, holding-period (LTCG vs STCG) logic, and realistic tax-aware selling. Investment accounts that hold individual securities (H3's concentrated position, H6's legacy stock and PE-adjacent holdings) populate lots; broadly diversified fund accounts may carry a single synthetic lot. `inherited_stepup` is required for H6 (assets stepped up at the late spouse's 2022 death). Holdings sold draw down specific lots and realize gain/loss against `basis_per_share`.

### A.5 Capital commitments (private funds)

Create table `capital_commitment`:

| Column             | Type               | Notes                                                              |
| ------------------ | ------------------ | ------------------------------------------------------------------ |
| `id`               | UUID PK            |                                                                    |
| `household_id`     | UUID FK            |                                                                    |
| `fund_name`        | encrypted text     | PII-adjacent; encrypt                                              |
| `committed_amount` | Decimal            |                                                                    |
| `called_to_date`   | Decimal            |                                                                    |
| `nav_account_id`   | UUID FK → accounts | account of new `account_type = 'private_fund'` holding current NAV |
| `vintage_year`     | int                |                                                                    |

Capital calls post as transfers out (category `capital_call`) that increase `called_to_date`; distributions post as inflows (category `capital_distribution`, an `investment_income` child). The defining demo value here is the irregular call/distribution cash-flow shape against an outstanding committed-but-uncalled balance — no other construct in the dataset produces it. Required for H6; optional enrichment for H3.

### A.6 Revolving credit lines (SBLOC / margin)

Extend the `account_type` enum with `sbloc` and `margin`. These are borrowing accounts carrying a negative balance with interest accrual but **no amortization schedule** — add a boolean `is_revolving` on `accounts` (default `false`) to distinguish them from the existing amortizing-loan handling so the debt-payoff projector does not attempt an amortization curve. Draws increase the balance (category `sbloc_draw`, a transfer); interest posts monthly (category `sbloc_interest`, an expense); paydowns reduce it. Required for H3 and H6.

### A.7 Advisory notes

Create table `advisory_note`:

| Column                               | Type               | Notes                                                                                       |
| ------------------------------------ | ------------------ | ------------------------------------------------------------------------------------------- |
| `id`                                 | UUID PK            |                                                                                             |
| `household_id`                       | UUID FK            |                                                                                             |
| `account_id` / `ownership_entity_id` | UUID FKs, nullable | optional anchor                                                                             |
| `category`                           | enum               | `estate`, `tax`, `concentration`, `insurance`, `retirement`, `charitable`, `scope_omission` |
| `title`                              | text               |                                                                                             |
| `body`                               | text               | the planning insight, in prose                                                              |
| `created_at`                         | timestamptz        |                                                                                             |

Advisory notes are how the review's findings persist as first-class data rather than code comments — the application can surface them in the relevant record's history/detail panel. Every household revision below specifies the advisory notes to seed. The `scope_omission` category is also used in Phase E to record intentional omissions household-by-household where relevant.

**Phase A acceptance criteria.** (1) `alembic upgrade head` applies cleanly and `downgrade` reverses. (2) New tables have correct grants — standard SELECT/INSERT/UPDATE for the app role, with `audit_log` untouched at SELECT/INSERT only. (3) An account titled in an `ilit` or `crt_*` entity is excluded from a household net-worth query; an account titled in a `revocable_trust` is included. (4) A permanent-life policy with a linked cash-value account contributes to net worth only when not ILIT-owned. (5) A vesting event creates a lot, an income transaction, and a sell-to-cover transfer atomically through an `@audit` service method. (6) Encrypted columns (`ownership_entity.name`, `capital_commitment.fund_name`) never appear in audit-log payloads.

---

## Phase B — Shared taxonomy additions

Add the following categories to `shared_categories.py`, all with `is_system = True`, created per-household alongside the existing taxonomy. Group them under existing parents where indicated.

Income categories: `rsu_vest_income` (→ employment_income), `nso_exercise_income` (→ employment_income), `espp_purchase` (→ employment_income; the discount element), `capital_distribution` (→ investment_income), `crt_income` (→ investment_income), `inherited_ira_rmd` (→ investment_income), `qcd_note` (a zero-income marker for QCD-satisfied RMD, excluded from taxable income — see note below).

Expense categories: `umbrella_premium` (→ insurance), `disability_insurance_premium` (→ insurance), `ltc_insurance_premium` (→ insurance), `permanent_life_premium` (→ insurance), `specialty_insurance_premium` (→ insurance), `sbloc_interest` (→ interest_expense), `private_school_tuition` (→ education), `advisory_fees` (already exists in H3 — promote to shared), `property_tax` (ensure present and high for NY/IL).

Transfer categories: `equity_sale` (diversification sale of vested/concentrated shares), `capital_call`, `sbloc_draw`, `daf_contribution` (transfer to donor-advised fund), `trust_funding` (funding a CRT/ILIT/revocable trust), `gift_to_ilit` (annual premium-funding gift), `annual_exclusion_gift` (gifts to family), `roth_conversion` (already conceptually present for H5; formalize), `529_superfund`.

**QCD handling note.** A Qualified Charitable Distribution satisfies an RMD while being excluded from taxable income, and it cannot route to a DAF. Model a QCD as an IRA-outflow transfer directly to a charity payee, tagged so the RMD-satisfaction logic credits it against the year's RMD but the income reports exclude it. Do not categorize a QCD as `inherited_ira_rmd` or as ordinary income.

---

## Phase C — Revisions to Households 1–5

Each subsection lists the concrete additions plus the advisory notes to seed. Preserve all existing data; these are additive except where noted. Re-run the per-household net-worth sanity check after revision and update the printed summary balances.

### C.1 H1 — Chen-Nakamura (Austin TX, ~$899K)

Add an **ESPP** at one member's employer: 15% discount with a lookback, contributions each pay period, shares purchased semi-annually, sold shortly after purchase (capturing the discount, minimal concentration). This introduces `equity_grant` (type `espp`), `vesting_event`-style purchase events, and lots. Add an **umbrella liability** policy ($1M, since net worth is approaching that line) and a **disability insurance** policy for the higher earner. Fold a brief **market dip** into the investment-account valuation snapshots (a drawdown across Q3 2024 recovering by mid-2025) so the net-worth series is non-monotonic. Optionally add a **mega-backdoor Roth** if the modeled employer plan supports after-tax contributions with in-plan conversion.

Advisory notes: one `insurance` note explaining that umbrella coverage should at least equal net worth and is low-cost relative to protection; one `concentration` note (even if minor) about selling ESPP shares promptly to avoid accidental employer-stock accumulation.

### C.2 H2 — Okonkwo-Rivera (Naperville IL, ~$3.4M)

This household's headline revision is the **Illinois state estate-tax exposure**, which is currently unexploited. Title the primary residence and a portion of the brokerage in a **revocable living trust** (`ownership_entity`, `revocable_trust`). Seed a prominent `estate` advisory note recording that Illinois imposes its own estate tax at a **$4,000,000 per-person exemption that is not indexed for inflation and not portable between spouses**, with graduated rates up to 16% and a cliff structure that taxes the entire estate once the threshold is crossed; that at ~$3.4M the household is just under the line but appreciation and life-insurance death benefits could push it over; and that the standard mitigation for a married couple is a **bypass/credit-shelter trust** at the first death to preserve both spouses' exemptions given the lack of portability. If the data model is to demonstrate the bypass-trust mechanism, add a second `irrevocable_trust` entity flagged for first-death funding, documented but unfunded in the current (both-living) state.

Add an **umbrella liability** policy ($3–5M) — reinforced by the rental property's tenant-liability exposure. Add **long-term-care** policies for both adults (standard pre-retirement consideration at this age/wealth). Add **529 superfunding**: a five-year-forward lump gift election into the dependents' 529s, plus a recurring **private-school tuition** expense line. If the "multi-generation" framing includes support to an aging parent, model recurring eldercare/gift transactions and note the sandwich-generation cash-flow.

Advisory notes: the `estate` note above; a `charitable`/`tax` note on the 529 superfunding gift-tax election; an `insurance` note on LTC timing.

### C.3 H3 — Whitfield-Torres (Brentwood CA, ~$9.5M) — priority retrofit

This is the most substantial revision. Replace part of the steady "business income" framing with a primary **equity-compensation** profile for the high earner: quarterly **RSU** vests with sell-to-cover across the window, plus an **ISO** grant with a held tranche that produces an **AMT** event in one tax year (set `amt_preference_amount`; seed a `tax` advisory note about the AMT year and credit carryforward). The accumulated vested shares plus direct holdings create a **concentrated single-stock position equal to roughly 30% of the investment portfolio** (populate `investment_lot` rows with `rsu_vest` and `purchase` basis). Add a **10b5-1-style scheduled diversification sale** that systematically trims the position over the 30 months (category `equity_sale`, realizing LTCG against lots), and seed a `concentration` advisory note explaining the ≥20%-of-net-worth concentration threshold and the rationale for systematic, pre-scheduled selling.

Add a **donor-advised fund** (`ownership_entity` is not required for a DAF, but model it as a held-away charitable account flagged `counts_in_personal_net_worth = false`) funded with **appreciated company stock** (avoiding capital gains, taking a deduction at the 30%-of-AGI limit for appreciated non-cash gifts), with periodic grants out. Add a **backdoor Roth** (non-deductible IRA contribution converted to Roth, since the household is over the direct-Roth income limit). Add a **securities-based line of credit** (`sbloc`) drawn to fund a large expense without triggering sales, with monthly interest and a partial paydown. Add a **revocable living trust** titling layer over the residence and taxable brokerage. Add **scheduled/specialty insurance** for a collectibles holding (a wine collection is on-brand for this household) and model the collection as a manually-valued collectible asset. Add a one-time **bonus/liquidity income spike**. In the property valuation history, seed a `tax` advisory note about the **California Proposition 13** divergence between the assessed basis and current market value.

Advisory notes: `concentration` (position sizing + 10b5-1 rationale), `tax` (AMT year; backdoor Roth; Prop 13 assessed-vs-market), `charitable` (appreciated-stock-to-DAF mechanics and the OBBBA 2026 0.5%-of-AGI floor / 35% deduction-benefit cap for top-bracket itemizers), `insurance` (scheduled coverage for the collection).

### C.4 H4 — Park-Cole (Nashville TN, ~$154.5K)

Add an **ESPP** at the startup-employed member. Optionally add a small **inherited IRA** (SECURE Act 10-year drawdown) as a realistic complexity if a recent parental death fits the narrative — this exercises the inherited-IRA pattern at the low end of the wealth range and pairs naturally with the household's age. Given the existing student loans, add a documented **married-filing-separately-for-IDR** consideration as a `tax` advisory note (filing separately can lower income-driven student-loan payments at the cost of MFS bracket treatment). Fold in a brief **unemployment gap** for one member (income stop + spend-down + recovery) so the early-career household shows a realistic discontinuity.

Advisory notes: `tax` (MFS-for-IDR tradeoff), `retirement` (inherited-IRA 10-year depletion deadline, if included).

### C.5 H5 — Langford (Sarasota FL, ~$12.86M)

Add a **Roth-conversion-window** pattern in the 2024 (pre-RMD) history: partial conversions filling lower brackets before RMDs and the primary member's age-73 transition push income and IRMAA tiers higher — this enriches the existing before/after RMD story. Add a **QCD** satisfying part of the post-transition RMD (tagged per the Phase B QCD note; remember it cannot route to a DAF). Add a **cash-value permanent life** policy that the member owns (cash value as a net-worth asset) framed as estate-liquidity provisioning. Add an **umbrella liability** policy ($10M). Add a **T-bill ladder / money-market** cash-management account in place of an oversized savings balance. Add **long-term-care** policies. Add a **revocable living trust** titling layer.

Advisory notes: `retirement`/`tax` (the Roth-conversion-window logic and its interaction with the IRMAA two-year lookback — a conversion in year N raises Medicare premiums in year N+2), `charitable` (QCD satisfying RMD while excluded from income), `insurance` (permanent life for estate liquidity; umbrella sizing).

---

## Phase D — New Household 6: Castellano (Scarsdale NY, ~$18.29M)

H6 is the most complex household and deliberately occupies the $15M–$20M band that no married couple in the set can use to demonstrate federal estate exposure (couples are now sheltered to $30M under OBBBA). It is a **single, widowed** individual, which also fills the otherwise-absent single-filer and single-member-RBAC cases, and it carries the full estate-and-legacy stack. Create `backend/scripts/seed_households/h6_castellano.py` and register `--household 6` in `seed_demo_data.py`.

### D.1 Overview and demographic context

Rosa Castellano, 74 (born 1951), widowed and retired, living in Scarsdale, Westchester County, New York. Her late husband David founded an industrial-products company that was acquired by a public company; David died in June 2022, two years before the seed window opens, and roughly half of the couple's jointly held assets received a step-up in basis at his death. Rosa's wealth is therefore a blend of long-held diversified investments, a low-basis legacy concentrated stock position (stepped up in 2022, appreciated since), inherited retirement assets, and real estate, organized around an estate plan built for wealth transfer to her two adult children (Marcus and Lucia, who are beneficiaries and successor advisors, **not** system members). New York is a high-income-tax state and, more importantly here, imposes an estate tax with a **$7,350,000 exemption, no portability, and a "cliff"** in which an estate exceeding 105% of the exemption is taxed on its **entire** value at rates up to 16% — so Rosa's ~$18.3M estate is fully exposed at the state level **and** ~$3.3M over the federal $15M exemption.

### D.2 Member roster and RBAC

A single primary member (Rosa). No partner, no dependents, no `account_access_grants` — this is the dataset's only **single-member** household and should exercise the degenerate RBAC case cleanly (one principal, full visibility, no grants table rows). Record the adult children as beneficiary metadata on the relevant trusts/DAF, not as members.

### D.3 Account and entity inventory (net-worth sanity check)

| Item                                  | Type                          | Value            | Notes                                                            |
| ------------------------------------- | ----------------------------- | ---------------- | ---------------------------------------------------------------- |
| Primary residence (Scarsdale)         | real_estate                   | 3,800,000        | titled in revocable trust; free and clear; ~$60K/yr property tax |
| Manhattan co-op (pied-à-terre)        | real_estate                   | 1,200,000        | titled in revocable trust; monthly maintenance                   |
| Diversified taxable brokerage         | brokerage                     | 3,400,000        | titled in revocable trust; single synthetic lot ok               |
| Legacy concentrated stock             | brokerage                     | 2,300,000        | one public ticker; lots: `inherited_stepup` basis ≈ 1,500,000    |
| Spousal rollover IRA                  | ira                           | 2,800,000        | RMDs at 74; QCD-eligible                                         |
| Inherited IRA (sister, d. 2023)       | inherited_ira                 | 620,000          | SECURE 10-year; full depletion by 2033                           |
| Roth IRA                              | roth_ira                      | 900,000          |                                                                  |
| Treasury / T-bill ladder              | private_fund? no → `treasury` | 700,000          | use existing cash-equivalent type or add `treasury`              |
| Money-market / brokerage cash         | brokerage                     | 400,000          |                                                                  |
| Checking                              | checking                      | 120,000          |                                                                  |
| Savings                               | savings                       | 180,000          |                                                                  |
| Whole-life cash value (owned by Rosa) | life_insurance_cash_value     | 410,000          | counts in NW (not ILIT-owned)                                    |
| Art collection                        | collectible                   | 800,000          | scheduled/specialty insured                                      |
| Private-equity fund NAV               | private_fund                  | 1,180,000        | committed 2,000,000; called 1,300,000; vintage 2021              |
| SBLOC drawn                           | sbloc (revolving)             | (520,000)        | against the diversified brokerage                                |
| **Personal net worth**                |                               | **≈ 18,290,000** |                                                                  |

Entities **excluded** from personal net worth (exercise the ownership-entity feature without inflating NW): the **CRT** (~$2.5M, Rosa holds only an income interest), the **ILIT** (owns a ~$3M permanent policy outside her estate), and the **DAF** (~$1.1M, irrevocably given). Each is an `ownership_entity` (or held-away charitable account for the DAF) with `counts_in_personal_net_worth = false` and, for the ILIT/CRT, `is_in_taxable_estate = false`.

### D.4 Trusts and charitable structures

- **Castellano Family Revocable Trust** (`revocable_trust`): titles the two properties and the diversified brokerage. In net worth, in the taxable estate — a pure titling/probate-avoidance layer. Seed an `estate` advisory note explaining a revocable trust avoids probate but does **not** reduce the taxable estate.
- **Castellano Irrevocable Life Insurance Trust** (`ilit`): owns a ~$3,000,000 permanent policy on Rosa's life, providing liquidity to her heirs to pay the combined federal + NY estate tax without forcing a fire-sale of illiquid assets. Rosa funds the ~$45,000 annual premium via **`gift_to_ilit`** transfers (annual-exclusion-style gifts). The policy's cash value is **not** in her net worth. Seed an `insurance`/`estate` note on the estate-liquidity rationale.
- **Castellano Charitable Remainder Unitrust** (`crt_crut`): funded in 2023 with appreciated low-basis stock; pays Rosa a 5% unitrust income stream (~$125,000/yr, taxed under the four-tier ordering rules), with a **DAF named as the remainder beneficiary** for flexibility. CRT assets are outside her net worth and estate. Seed a `charitable` note on the capital-gains-deferral-plus-income-plus-deduction mechanics and the DAF-as-remainder flexibility.
- **Donor-Advised Fund**: ongoing giving vehicle; periodic appreciated-stock contributions and grants out; successor advisors are the two children. Excluded from personal net worth.

### D.5 Income streams (active, decumulation)

- **Social Security survivor benefit** (~$4,200/mo) — Rosa claims the survivor benefit on David's record (higher than her own); monthly deposit.
- **RMD from spousal rollover IRA** (~$110,000/yr at age 74), with ~$50,000/yr satisfied by **QCD** (excluded from income, credited against the RMD, paid to charity directly — not to the DAF).
- **Inherited IRA RMD** (separate SECURE 10-year schedule; must fully deplete by 2033).
- **CRT unitrust income** (~$125,000/yr, quarterly).
- **Brokerage dividends + T-bill ladder interest** (recurring).
- **PE fund distribution** (irregular — one ~$220,000 distribution in the window).

No pension (deliberately omitted to keep H6 distinct from H5's defined-benefit story).

### D.6 Notable transaction patterns and events (Jan 2024 – Jun 2026)

Beyond the recurring income above: **PE capital calls** of ~$150,000 (Mar 2024) and ~$180,000 (Nov 2024) against the outstanding commitment, and the ~$220,000 distribution (Sep 2025). An **SBLOC draw** of $520,000 in 2024 to fund annual-exclusion gifts to children and grandchildren plus a residence renovation, with monthly `sbloc_interest` and a partial paydown in 2025. **Annual-exclusion gifts** ($19,000 per recipient across children and grandchildren) each year, tagged `annual_exclusion_gift` — a documented estate-reduction strategy that is especially clean in states with no gift tax. **Systematic diversification sales** of the legacy concentrated position (quarterly trims realizing LTCG against the `inherited_stepup` lots). High **Westchester property tax** (~$60K/yr) and co-op maintenance. **Medicare at the top IRMAA tier for a single filer** (Part B + Part D surcharges reflecting her high income — reuse H5's IRMAA machinery but apply the **single-filer** thresholds and top tier), plus Medigap. Premiums for the **umbrella ($10M)**, **LTC**, **whole-life**, and **scheduled art** policies. A modest **art acquisition**. Reflect the **2024 market dip** in investment snapshots consistent with the other households.

### D.7 FIRE / scenario configuration

A single decumulation scenario is sufficient (this is not an accumulation household), but it should be a multi-stream JSONB income array exercising: `social_security` (survivor), `other` (CRT income), `investment` (RMD + dividends + T-bill interest), and an irregular `other` for PE distributions, with the inherited-IRA depletion modeled as a declining stream ending 2033. The scenario's value is demonstrating a sustainable single-life decumulation against a large, partly illiquid, estate-tax-exposed balance sheet — not an accumulation-to-FI projection.

### D.8 Budget configuration

A decumulation budget effective 2024-01-01 with realistic high-net-worth single-retiree lines: property tax (high), home maintenance, co-op maintenance, travel, healthcare (Medicare Part B + IRMAA top tier, Part D, Medigap), advisory fees (on a large managed portfolio), charitable (separate from QCD/DAF/CRT — discretionary giving), personal care, clubs/events, gifts, and the insurance premiums above. Include at least one **budget-history** row (e.g., an IRMAA/Medicare line stepping up across 2024→2025→2026 as income and indexed surcharges rise), keeping H6 consistent with the dataset-wide budget-history coverage.

### D.9 H6 advisory notes (seed all)

An `estate` note on the **federal exposure** (~$3.3M over the permanent $15M exemption, 40% top rate) and the **New York cliff** (entire ~$18.3M estate exposed once over 105% of the $7.35M exemption, up to 16%), and why the combination drives the ILIT liquidity planning. A `retirement` note on the **inherited-IRA 10-year depletion** deadline. A `concentration` note on the legacy single-stock position and the step-up basis from 2022. A `charitable` note tying the **CRT + DAF + QCD** together as a coordinated strategy. A `tax` note on **single-filer** brackets and **single-filer IRMAA** thresholds differing from married. An `insurance` note on the **whole-life-as-asset vs. ILIT-owned-policy** distinction (why one counts in net worth and the other does not).

---

## Phase E — Documenting intentional omissions for posterity

Create `~/Documents/hearthledger-spec/docs/scope-boundaries.md` recording, in prose, the deliberate upper boundary of the system and the situations intentionally left out so future contributors do not read their absence as oversight. The document should state that HearthLedger targets households up to roughly $20M net worth and is a **tracking and reporting** system, not a tax-preparation engine: AMT, IRMAA, RMD, and estate exposures are modeled as **patterns and advisory notes in the data**, never as computed filings. It should then enumerate the intentional omissions and the reasoning:

- **Multi-currency, foreign accounts, and FX** — v1 is USD-only; FBAR/FATCA reporting and currency translation are out of scope.
- **Family-office and ultra-HNW structures** — captive insurance, private-placement life insurance (PPLI), family limited partnerships, and **funded** GRATs/SLATs/IDGTs/dynasty trusts belong to the >$20M world and are the deliberate ceiling. The system supports **revocable**-trust titling and, as the single intentional step over the line, an **ILIT and CRT** on the H6 single-filer household (justified by the $15M federal boundary); other irrevocable funded vehicles are excluded.
- **Gross-salary / payroll-deduction granularity** — deferred to v2 per the original spec; equity-compensation withholding **detail** inherits this deferral, while vest **events** and net **positions** are in scope.
- **Active tax-return preparation / filing logic** — out of scope by design.
- **Crypto / digital assets** — mechanically supportable (another valued asset) but intentionally left as a future optional addition rather than a v1 requirement.

Also seed a small set of household-level `advisory_note` rows with `category = scope_omission` where a household sits near a boundary (e.g., an H6 note that funded irrevocable transfer vehicles beyond the ILIT/CRT are out of scope; an H3 note that PPLI and captive structures are out of scope at its level), so the boundary is visible in-app and not only in the docs.

---

## Phase F — Updated coverage matrix and acceptance criteria

After all phases, the printed `--household all` summary should show six households:

```
H1  Chen-Nakamura    Austin TX      Members: 2  NW: ~$898,900
H2  Okonkwo-Rivera   Naperville IL  Members: 4  NW: ~$3,407,800
H3  Whitfield-Torres Brentwood CA   Members: 4  NW: ~$9,463,400
H4  Park-Cole        Nashville TN   Members: 2  NW: ~$154,500
H5  Langford         Sarasota FL    Members: 2  NW: ~$12,856,700
H6  Castellano       Scarsdale NY   Members: 1  NW: ~$18,290,000

Six states; NW range $154,500 → $18,290,000 (118× spread).
Estate exposure represented: state-only (IL, H2), none-federal-couple (H3/H5),
  federal + state cliff single-filer (NY, H6).
```

Update the cross-household feature matrix to add rows for: equity compensation (RSU/ISO/NSO/ESPP), concentrated position, cost-basis lots, revocable trust, ILIT, CRT, DAF, QCD, backdoor Roth, Roth-conversion window, inherited IRA, capital commitments, SBLOC, umbrella liability, permanent/cash-value life, disability, LTC, scheduled/specialty, collectible asset, single-member RBAC, single-filer tax, and market-dip discontinuity — mapping each to the households above.

**Final acceptance criteria.** (1) `--household 6` and `--household all` run clean and idempotently under deterministic seeding. (2) Each household's computed net worth matches its sanity-check target within rounding. (3) H6 produces exactly one principal and zero `account_access_grants`. (4) ILIT/CRT/DAF assets are excluded from H6 net worth and taxable-estate figures; the revocable trust's assets are included in both. (5) Every advisory note specified in Phases C–E exists and is anchored to the correct household/account/entity. (6) `docs/scope-boundaries.md` exists and enumerates the five intentional omissions with reasoning. (7) A vesting event in H3 atomically creates a lot, income transaction, and sell-to-cover transfer via an `@audit` method; a capital call in H6 increases `called_to_date` and posts a `capital_call` transfer; an SBLOC draw posts a `sbloc_draw` transfer and monthly `sbloc_interest`. (8) No new encrypted field appears in any audit-log payload.

---

## Appendix — New-table quick reference

`ownership_entity` (trusts/titling) · `insurance_policy` (+ optional `life_insurance_cash_value` account) · `equity_grant` + `vesting_event` · `investment_lot` (cost basis) · `capital_commitment` (+ `private_fund` account) · `advisory_note`. Account-type enum extended with `sbloc`, `margin`, `private_fund`, `life_insurance_cash_value`, and (if not present) a cash-equivalent `treasury`. New FKs: `ownership_entity_id` on `accounts` and `real_estate_properties`; `is_revolving` boolean on `accounts`.

_All tax thresholds herein are 2025–2026 figures (federal exemption $15M; annual gift exclusion $19,000; QCD limit ≈ $108,000 for 2025; IL estate exemption $4M; NY estate exemption $7.35M with 105% cliff) and should be re-verified at implementation against current IRS and state figures._

_End of HearthLedger Demo Dataset Revision & Extension Spec._
