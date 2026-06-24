# Design: Member Financial-Identity Layer (DOB + age-based calculations)

Status: Proposed
Origin: `/plan-ceo-review` 2026-06-24 (SELECTIVE EXPANSION, Approach C)

## Problem (corrected premise)

The original request was "add date-of-birth as an attribute for **users**." Corrected:
DOB belongs on `HouseholdMember` (the person), not `User` (the auth account), and the
column **already exists** end to end (model, schemas, `member` service, provisioning,
`PATCH /members/{id}`). Two real gaps remain:

1. DOB has **no input in the UI** — the Members edit drawer renders only Display name +
   Role, so DOB can only be set via seed/provisioning/API today.
2. The app cannot reason about a person's age to model **age-triggered cash events** —
   RMDs (age 73), and future Social Security / Medicare / 59½ gates. RMD today is only a
   transaction category in the cash-flow breakdown, not a computed engine.

## What already exists (reused, not rebuilt)

- `HouseholdMember.date_of_birth` (plaintext `Date`) + `MemberCreate/Update/Response`.
- `fire_service` → `fire_projector.project(scenario, from_year, dob)` already passes member
  DOB and computes per-year age (precision bug: `age = year - dob.year` ignores month/day).
- Pension `eligibility_age` / `eligibility_date` — the age-gating pattern to mirror.
- Snapshot-based retirement balances + `report.py` batched-balance reads.
- `@audit` on member mutations; TanStack form patterns in `Members.tsx`.

## Scope (this program)

Accepted:

- Member financial-identity layer: `member.retirement_target_age` + `account.tax_treatment`
  (pretax / roth / taxable).
- DOB editable: Members drawer field, member-create form, self-service "Your profile" under
  the user dropdown.
- `age.py` pure service: month/day-accurate `current_age`, `age_at_year`, milestone dates.
- RMD engine (`rmd.py`): age-73 trigger, IRS Uniform Lifetime Table divisor, pretax balances.
- FIRE age-precision fix + RMD wired into supplemental income / withdrawal need.
- Age-milestone timeline UI.

Deferred (NOT in scope):

- Social Security claiming-age modeling — self-contained engine, own PR.
- Filing status — only pays off with a tax engine.
- State of residence — needs state-tax logic (not scheduled).
- Roth-conversion modeling — depends on tax_treatment + a tax estimate.
- Federal/state tax-estimate engine — XL, ongoing table maintenance, own program.

## Key decisions

1. **RMD balance source:** require an explicit prior-year **Dec-31 snapshot** per pretax
   account; show a "add a year-end balance" empty/partial state when missing. Most faithful
   to the IRS rule (RMD = prior-year-end balance ÷ divisor).
2. **DOB at rest:** keep the **plaintext `Date`** column. It is pre-existing, FIRE filters it
   in SQL, and it is not in CLAUDE.md rule 6's encrypted account-identifying PII list.
3. **DOB edit authorization:** **self-or-primary** — a user may edit their own linked
   member's DOB; primary members may edit anyone. Role changes stay primary-only.
4. **Tax treatment:** explicit nullable `tax_treatment` enum on accounts, **seeded from
   account_type** where unambiguous and user-overridable. Same field future Roth-conversion
   modeling will need.

## Architecture

```
  HouseholdMember.date_of_birth ──┐
  + retirement_target_age         ├──▶ age.py (pure: current_age, age_at_year, milestones)
  Account.tax_treatment ──────────┘            │                 │
  (pretax/roth/taxable)                        ▼                 ▼
  Snapshot (Dec-31 prior-year) ──────▶ rmd.py (age-73,    fire_projector
                                        Uniform Lifetime    (age fix; RMD in
                                        divisor, pretax)    as supplemental)
  GET /reports/required-distributions ◀────────┘
  Profile page + Members DOB field ──▶ PATCH /members/{id} (self-or-primary)
```

## Failure modes (all rescued, all tested, none silent)

| Codepath         | Failure            | Rescue              | User sees                |
| ---------------- | ------------------ | ------------------- | ------------------------ |
| age.current_age  | dob None           | return None         | "Add your birthdate"     |
| age.current_age  | dob in future      | reject (validation) | field error              |
| rmd.project      | no DOB / age<73    | return []           | "RMDs begin {year}"      |
| rmd.project      | no Dec-31 snapshot | return []           | "Add a year-end balance" |
| rmd.project      | no pretax account  | return 0            | "No pretax balances"     |
| rmd divisor      | age > table max    | clamp to floor      | no crash                 |
| PATCH member DOB | not self/primary   | 403                 | permission error         |

## Sequencing (multi-PR — baseline touches ~12 files)

- **PR1:** identity-layer schema (two additive reversible migrations) + DOB editing UI
  (Members + Profile, self-or-primary authz) + `age.py` + FIRE age fix.
- **PR2:** `rmd.py` engine + `GET /reports/required-distributions` + FIRE wiring + tests.
- **PR3:** age-milestone timeline UI (LOADING / EMPTY / PARTIAL / ERROR states).

## Implementation tasks

| ID  | P   | Component     | Title                                                                     |
| --- | --- | ------------- | ------------------------------------------------------------------------- |
| T1  | P1  | schema        | member.retirement_target_age + account.tax_treatment migrations           |
| T2  | P1  | age-service   | age.py pure service; replace fire_projector inline age                    |
| T3  | P1  | validation    | reject future-dated DOB                                                   |
| T4  | P1  | rmd-engine    | rmd.py: age-73, Uniform Lifetime divisor (clamp 120+), Dec-31 pretax base |
| T5  | P1  | api           | GET /reports/required-distributions + schemas + integration test          |
| T6  | P1  | tax-treatment | seed/backfill tax_treatment; override select in account form              |
| T7  | P1  | ui-members    | DOB field in Members drawer + create form                                 |
| T8  | P1  | ui-profile    | Your Profile page; self-or-primary authz in member service                |
| T9  | P2  | fire          | wire RMD into FIRE; fix age precision                                     |
| T10 | P2  | ui-timeline   | age-milestone timeline (empty/partial states)                             |
| T11 | P2  | tests         | age boundaries; rmd matrix; endpoint pretax-vs-Roth                       |
| T12 | P2  | observability | structured log in rmd.project                                             |
| T13 | P3  | design        | /plan-design-review on the timeline                                       |
