# HearthLedger — Demo Data Revision & H6 Implementation Plan

**Status:** Plan only. No code written. Produced via `/office-hours` (plan-only mode) on 2026-06-22.
**Implements:** `docs/hearthledger-demo-data-revision-spec.md` (Phases A–F).
**Grounded against:** the actual `financial-dashboard` codebase as of `c0a87af` (v0.9.4.0), not the spec's assumed paths.
**Companion docs:** `hearthledger-demo-data-review.md` (gap analysis), reference spec at `~/Documents/hearthledger-spec/docs/data-model.md`.

---

## TL;DR

The spec reads as "revise the demo data," but its own Phase A acceptance criteria
demand new tables wired into **visibility, `@audit` services, encryption, and
net-worth math** with reversible migrations. That is full-stack backend feature
work, not seed-script edits. The seed scripts write models directly as the DB owner
and bypass the service/`@audit` layer entirely (confirmed in
`seed_demo_data.py`), so "make the generators populate the tables" and "satisfy
the Phase A acceptance criteria" are two different jobs.

**The one decision that triples or thirds the effort** is how much application
surface the new tables get. See [Decision 1](#decision-1-application-surface-the-big-fork).

Everything else is mechanical once that is settled. Below: what the spec gets
wrong about this codebase, the corrected phase plan with real file paths, an
acceptance-criteria traceability table, the migration gotchas, and an effort estimate.

---

## Codebase reality vs. the spec (read this first)

These are concrete mismatches between the spec's assumptions and the actual code.
Each one would bite during implementation.

### 1. `account_type` names in the spec do not exist in the enum
`backend/app/db/models/account.py:10` defines `ACCOUNT_TYPES` as a Postgres native
enum (`name="account_type"`, `create_type=False`). The actual values are
`investment_brokerage`, `retirement_ira`, `retirement_roth_ira`, etc. The spec's H6
inventory (D.3) uses `brokerage`, `ira`, `roth_ira`, and **`inherited_ira`** — none
of which match, and `inherited_ira` does not exist at all.
- **Resolution:** map `brokerage → investment_brokerage`, `ira → retirement_ira`,
  `roth_ira → retirement_roth_ira`. Decide `inherited_ira`: add it as a real enum
  value (recommended — H4 and H6 both need it, and the SECURE 10-year drawdown is a
  distinct pattern worth its own type) or ride on `retirement_ira` plus metadata.
- New enum values to add per the spec: `sbloc`, `margin`, `private_fund`,
  `life_insurance_cash_value`, and a cash-equivalent `treasury` (plus `inherited_ira`
  if chosen).

### 2. Adding Postgres enum values is a migration trap and is not cleanly reversible
`ALTER TYPE account_type ADD VALUE ...` cannot be used in the same transaction that
later references the new value, and Alembic wraps each migration in a transaction.
Postgres also has **no `DROP VALUE`**, so a literal reversible `downgrade()` requires
recreating the type and recasting the column. This collides directly with the
project's "migration is reversible (has `downgrade()`)" checklist item.
- **Resolution:** isolate enum additions in their own migration step using
  autocommit (`op.execute("COMMIT")` or `connection.execution_options(isolation_level="AUTOCOMMIT")`),
  and document the enum-additions `downgrade()` as the standard "recreate-type" dance
  or an explicit, justified no-op. Flag this in the PR description so the design-review
  checklist item is consciously waived, not silently failed.

### 3. Net-worth math keys off a different field than the spec assumes
Net worth is computed by filtering `account.include_in_net_worth` (boolean on
`accounts`), at `backend/app/services/report.py:231` and `:252`, and
`backend/app/services/fire_detector.py:223`. The spec introduces a **second**
gate, `ownership_entity.counts_in_personal_net_worth`, plus a brand-new
`is_in_taxable_estate` concept that no report currently computes.
- **Resolution:** the net-worth predicate becomes `include_in_net_worth AND
  (ownership_entity_id IS NULL OR entity.counts_in_personal_net_worth)`. This must
  be applied in `report.py` (both sites), `fire_detector.py:223`, and anywhere
  real-estate value rolls up. Estate-exposure reporting (`is_in_taxable_estate`) is
  net-new surface — there is no existing report to extend, so scope it explicitly
  (new report method, or advisory-note-only with no computed figure — see Decision 1).

### 4. Phase B categories do not map onto the existing taxonomy
`Category` (`backend/app/db/models/category.py`) has only `is_income` (bool) plus a
parent hierarchy. There is no "transfer" category type and no `interest_expense` or
`insurance` parent. The shared taxonomy lives as a flat `_DEFS` list in
`backend/scripts/seed_households/shared_categories.py`; insurance currently sits at
`financial_services > life_insurance`, and there is no interest-expense parent.
The spec's `umbrella_premium → insurance` and `sbloc_interest → interest_expense`
reference parents that do not exist.
- **Resolution:** either add new parent categories (`insurance`, `interest_expense`)
  to `_DEFS` or graft the new leaves under `financial_services`. Transfers are modeled
  as `is_income=False` rows (consistent with existing `cc_payment`, `mortgage_payment`,
  etc.). Adding rows to `_DEFS` propagates to every household via `seed_categories()`,
  so this is one edit, not six.

### 5. New encrypted fields must be named to hit the audit exclusion set
`backend/app/core/audit.py:12` excludes encrypted fields by **exact column name**
(`ENCRYPTED_FIELDS`). A column literally named `name` (spec A.1 for
`ownership_entity.name`) or `fund_name` (A.5) would **leak into the audit log** —
directly violating AC #6.
- **Resolution:** follow the `Account` pattern — store as `BYTEA`/`LargeBinary`
  columns named `name_enc` and `fund_name_enc`, and add both to `ENCRYPTED_FIELDS`
  in `audit.py`. Encryption itself reuses `backend/app/core/encryption.py`.

### 6. The seed path bypasses services and `@audit` by design
`seed_demo_data.py` runs as the DB owner, calls `session.add(...)` directly, and even
deletes from `audit_log` (line 108–119, an accepted dev-tooling exception). So
populating the new tables in the generators does **not** exercise `@audit` service
methods. Phase A AC #5/#7 (vesting/capital-call/SBLOC via `@audit`) are about the
**application** layer and must be satisfied by real service methods + tests, separate
from seeding. Do not assume the seed run proves those ACs.

### 7. Seeder registration is two dicts + an import
Adding H6 means: create `backend/scripts/seed_households/h6_castellano.py`, import it
in `seed_demo_data.py:37`, add `6: h6_castellano.seed` to `_SEEDERS` (line 49), and
`6: "Castellano Household"` to `_HOUSEHOLD_NAMES` (line 57). Deterministic RNG is
`random.Random(42 + num)` (line 250/267), so H6 gets seed `48` for free. The
`--household` argparse `choices` derive from `_SEEDERS`, so `--household 6` and
`--household all` start working automatically.

---

## Decision 1: application surface (the big fork)

The new tables need, at minimum, to exist and feed net-worth math. The question is how
far up the stack they go. This is the single largest effort driver.

| Option | What it includes | Effort | Best when |
|---|---|---|---|
| **A. Data-model + seed only** | Models, migration, net-worth/estate aggregation wiring in `report.py`, encryption, seed generators (C–F). No new repositories/services/API/frontend. `@audit` service methods built **only** as far as ACs #5/#7 strictly require (thin services covering vest/capital-call/SBLOC create paths) + their unit tests. | **M–L** | The goal is a richer demo dataset and the data-model foundation, with UI/API deferred. |
| **B. + read API & frontend display** | Option A plus Pydantic schemas, read endpoints, and `get_visible`-routed repositories so the app can actually surface advisory notes / entities / lots in detail panels (A.7's stated intent). Integration tests per CLAUDE.md. | **L–XL** | You want the demo to *show* the new structures in the UI, not just compute correct net worth. |
| **C. Full CRUD feature set** | Option B plus write endpoints, forms, full `@audit` coverage across all new tables, frontend mutation flows. | **XL+** (multi-PR) | These become first-class user-editable features, not demo-only scaffolding. |

**Recommendation: A**, scoped as the first PR, with B as an explicit fast-follow if the
demo needs to display the new data. Rationale: the spec's own framing is "demo dataset
revision + extension"; the acceptance criteria test correctness of net-worth/estate
math and atomic `@audit` mutations, not UI. Option A satisfies every stated AC. Building
full CRUD/UI (C) for tables that exist mainly to enrich seeded demo households is
boiling a different ocean. If you want the advisory notes visible in-app, take B for the
read path only.

**This plan is written assuming Option A.** If you pick B or C, add the API/frontend/test
rows noted inline.

---

## Phase plan (corrected, with real file paths)

Execute A → B → (C/D/E in any order) → F, per the spec. Phase A is the hard prerequisite.

### Phase A — schema additions
**New migration:** `backend/alembic/versions/0007_demo_data_extension.py` (next in the
`000N_` sequence; current head is `0006`). Consider splitting enum-value additions into
`0007a` to isolate the autocommit requirement (see mismatch #2).

**New models** in `backend/app/db/models/` (register each in `models/__init__.py`):
- `ownership_entity.py` — `OwnershipEntity`. `name_enc BYTEA` (encrypted), `entity_type`
  enum, `is_in_taxable_estate`, `counts_in_personal_net_worth`, `grantor_member_id` FK.
- `insurance_policy.py` — `InsurancePolicy`. `metadata JSONB`, optional
  `cash_value_account_id` FK, optional `owner_ownership_entity_id` FK.
- `equity_grant.py` — `EquityGrant` + `vesting_event.py` `VestingEvent` (or one file).
  `vesting_schedule JSONB`. `VestingEvent.resulting_lot_id` FK → `investment_lot`.
- `investment_lot.py` — `InvestmentLot`. `basis_type` enum incl. `inherited_stepup`.
- `capital_commitment.py` — `CapitalCommitment`. `fund_name_enc BYTEA` (encrypted),
  `nav_account_id` FK.
- `advisory_note.py` — `AdvisoryNote`. `category` enum incl. `scope_omission`, nullable
  `account_id` / `ownership_entity_id` anchors.

**Column additions:**
- `accounts`: `ownership_entity_id UUID NULL FK`, `is_revolving BOOLEAN NOT NULL DEFAULT false`.
- `real_estate_properties`: `ownership_entity_id UUID NULL FK`.
- `account_type` enum: add `sbloc`, `margin`, `private_fund`, `life_insurance_cash_value`,
  `treasury` (+ `inherited_ira` per Decision in mismatch #1).

**Grants:** mirror the baseline pattern in `0001_baseline.py` — standard
`SELECT, INSERT, UPDATE` for the app role on every new table; leave `audit_log`
untouched at `SELECT, INSERT` only.

**Aggregation wiring (the real work):**
- Extend the net-worth predicate in `report.py:231`, `report.py:252`,
  `fire_detector.py:223` to respect `counts_in_personal_net_worth` (mismatch #3).
- Decide estate-exposure surface for `is_in_taxable_estate` (new report method vs.
  advisory-note-only). Under Option A, advisory-note-only is the lighter, AC-satisfying
  choice; the figure lives in the note prose, not a computed report.

**Audit/encryption wiring:**
- Add `name_enc`, `fund_name_enc` to `ENCRYPTED_FIELDS` in `audit.py:12`.
- Thin `@audit` service methods for the mutation paths ACs #5/#7 require:
  vesting-event create (atomic lot + income txn + sell-to-cover transfer),
  capital-call posting, SBLOC draw. Place in `backend/app/services/`. These are the
  only services Option A requires.

**Phase A acceptance criteria** map 1:1 to the spec's six; see traceability table below.

### Phase B — shared taxonomy
Edit `backend/scripts/seed_households/shared_categories.py` `_DEFS` only. Add the
income/expense/transfer leaves from spec §Phase B, reconciling parents per mismatch #4
(add `insurance` and `interest_expense` parents, or graft under `financial_services`).
Implement the QCD-as-IRA-outflow-to-charity tagging convention (a transfer category
`qcd_note` excluded from income reports) — this is a seed-data tagging rule, plus a
read-side filter wherever income is summed if QCDs must be excluded from taxable-income
displays.

### Phase C — revise H1–H5
Additive edits to the five existing generators (sizes today: h1 22KB, h2 30KB, h3 38KB,
h4 26KB, h5 39KB). Per the spec:
- **h1_chen_nakamura.py:** ESPP grant + purchase events + lots; umbrella + DI policies;
  market-dip in snapshot valuations (Q3 2024 → mid-2025); optional mega-backdoor Roth.
  2 advisory notes (`insurance`, `concentration`).
- **h2_okonkwo_rivera.py:** revocable trust titling the residence + brokerage slice;
  prominent IL state-estate `estate` note; documented-but-unfunded bypass `irrevocable_trust`;
  umbrella; LTC for both adults; 529 superfund + private-school tuition. 3 notes.
- **h3_whitfield_torres.py:** the priority retrofit — RSU quarterly vests + sell-to-cover;
  ISO held tranche → AMT event (`amt_preference_amount`); ~30%-of-portfolio concentrated
  position (lots: `rsu_vest` + `purchase`); 10b5-1 scheduled `equity_sale` trims; DAF
  (held-away, `counts_in_personal_net_worth=false`) funded with appreciated stock;
  backdoor Roth; SBLOC draw + interest + paydown; revocable trust; scheduled wine-collection
  policy + collectible asset; bonus/liquidity spike; Prop 13 note. 4+ notes.
- **h4_park_cole.py:** ESPP; optional small inherited IRA (SECURE 10-yr); MFS-for-IDR
  `tax` note; unemployment gap (income stop + spend-down + recovery). 1–2 notes.
- **h5_langford.py:** Roth-conversion-window in 2024 pre-RMD history; QCD satisfying part
  of the RMD (per the QCD tagging rule, not routed to DAF); cash-value whole-life (owned,
  counts in NW); umbrella $10M; T-bill ladder / MMF account; LTC; revocable trust. 3 notes.

After each, re-run the per-household net-worth sanity check and update the printed
summary (spec Phase F targets).

### Phase D — new H6 Castellano
Create `backend/scripts/seed_households/h6_castellano.py` mirroring `h5_langford.py`'s
structure (most similar: retired, decumulation). Wire into `seed_demo_data.py` per
mismatch #7. Implement the D.3 inventory (≈ $18.29M NW), the four trust/charitable
structures (revocable trust in-NW; ILIT, CRT, DAF excluded), single-member RBAC (one
`primary`, zero `account_access_grants`), the decumulation income streams (SS survivor,
RMD with QCD, inherited-IRA RMD, CRT unitrust, dividends/T-bill, irregular PE
distribution), the transaction patterns (PE capital calls, SBLOC draw, annual-exclusion
gifts, systematic diversification sales of the `inherited_stepup` lots, Westchester
property tax, single-filer top-tier IRMAA), one decumulation FIRE scenario (multi-stream
JSONB), a decumulation budget with one budget-history step, and all D.9 advisory notes.

### Phase E — scope-boundaries doc
Create `~/Documents/hearthledger-spec/docs/scope-boundaries.md` (note: **reference-spec
repo, not this repo** — the spec is explicit about the path). Enumerate the five
intentional omissions with reasoning. Seed `scope_omission` advisory notes on H3
(PPLI/captive out of scope) and H6 (funded irrevocable vehicles beyond ILIT/CRT out of
scope).

### Phase F — coverage matrix + acceptance
Update the printed `--household all` summary to six households with the spec's NW targets;
extend the cross-household feature matrix (wherever it lives in docs) with the new rows.
Verify all 8 final acceptance criteria.

---

## Acceptance-criteria traceability

| AC | Where satisfied | Test |
|---|---|---|
| A.1 migration up/down clean | `0007*` migration; enum downgrade caveat (mismatch #2) | `alembic upgrade head` + `downgrade` in CI |
| A.2 grants correct, audit_log untouched | migration `GRANT` block | grant assertion test |
| A.3 ILIT/CRT excluded, revocable included | `report.py` predicate change (mismatch #3) | net-worth unit test per entity type |
| A.4 ILIT-owned cash value excluded | net-worth predicate + `insurance_policy` link | unit test |
| A.5 vesting atomic via `@audit` | new `@audit` service method | service unit test + audit-row assertion |
| A.6 encrypted cols never in audit | `name_enc`/`fund_name_enc` in `ENCRYPTED_FIELDS` | `@audit` exclusion test |
| F.1 `--household 6`/`all` idempotent | seeder registration + `_household_exists` guard | seed run |
| F.2 NW within rounding | per-household sanity checks | seed summary assertions |
| F.3 H6 one principal, zero grants | H6 generator | inspect/count test |
| F.4 entity NW/estate inclusion | predicate change | unit test |
| F.5 every advisory note exists | C–E generators | count/anchor test |
| F.6 scope-boundaries.md exists | Phase E | file-exists check |
| F.7 vest/capital-call/SBLOC postings | services + generators | service + seed assertions |
| F.8 no encrypted field in audit | audit exclusion | exclusion test |

---

## Testing plan (per CLAUDE.md)

- **Unit:** net-worth predicate across all entity-type/`counts_in` combinations;
  `@audit` row written + encrypted fields excluded for each new mutating service;
  vesting-event atomicity (lot + income + sell-to-cover in one commit); QCD income
  exclusion.
- **Migration:** `upgrade head` then `downgrade` reverses (with the documented enum
  caveat).
- **Seed:** `--household 6` and `--household all` run clean and idempotent under fixed
  RNG; computed NW matches each sanity target within rounding; H6 yields exactly one
  member and zero grants.
- **(Option B/C only):** integration tests for any new endpoints; frontend component/
  hook tests for any new display/forms.

---

## Effort & sequencing

- **PR 1 — Phase A (schema + wiring + thin services + tests).** Hard prerequisite.
  Highest-risk PR (migration enum trap, net-worth predicate change touches FIRE +
  reports). **M–L** under Option A.
- **PR 2 — Phase B + C (taxonomy + H1–H5 revisions).** **L** (H3 is the bulk).
- **PR 3 — Phase D (H6).** **M–L**.
- **PR 4 — Phase E + F (scope doc + coverage matrix + final ACs).** **S–M**.

Splitting Phase A from the seed work is strongly advised: it isolates the
invariant-touching changes (audit/visibility/encryption/net-worth) behind their own
review and test gate before any household generator depends on them.

---

## Open decisions for you

1. **Application surface** — Option A / B / C above. (Recommend A, B-read as fast-follow.)
2. **`inherited_ira` enum value** — add it (recommended; H4 + H6 need it) or fold into
   `retirement_ira` + metadata?
3. **`is_in_taxable_estate` reporting** — computed estate-exposure report, or
   advisory-note-only prose figure (recommended under Option A)?
4. **Enum-addition `downgrade()`** — recreate-type dance, or documented no-op with the
   design-review checklist item consciously waived?
5. **Phase B parents** — add `insurance` / `interest_expense` parent categories, or graft
   new leaves under existing `financial_services`?
6. **Scope-doc location** — confirm `scope-boundaries.md` goes in the **reference-spec
   repo** (`~/Documents/hearthledger-spec/docs/`) per the spec, not this repo's `docs/`.

---

*Plan only. Greenlight a scope option and I'll implement, starting with Phase A as its own PR.*
