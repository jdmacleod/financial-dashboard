# TODOS

### WCAG 2.1 AA accessibility audit — HearthLedger v1 (Post-Phase 7)

**What:** Run a full WCAG 2.1 AA audit across all HearthLedger pages: color contrast ratios (4.5:1 body text, 3:1 large text), screen reader label completeness, keyboard navigation order, and focus indicator visibility.

**Why:** Phase 7 adds basic a11y specs (visible labels, 44px targets, checkbox roles) but stops short of WCAG 2.1 AA. A future audit closes the gap for any household member with visual or motor accessibility needs.

**Pros:** Identifies contrast failures early (especially `indigo-600` on white for small text). Screen reader labels for charts (Recharts) are commonly missing and won't be caught without a dedicated pass.

**Cons:** Time-consuming manual audit. Recharts doesn't support ARIA chart roles natively — fixing charts requires workarounds.

**Context:** Found during Phase 7 design review. Basic a11y specs now in plan (design decision 14). Full WCAG audit deferred to avoid blocking Phase 7 implementation.

**Depends on:** Phase 7 implementation complete.

---

### Investment positions — optional brokerage sync (residual)

**What:** Auto-populate positions from an external brokerage provider. The manual
positions feature — per-ticker rollup ("Top positions") and "Holdings mix by asset class"
donut — is implemented (see Completed below). Only the optional brokerage-sync leg of the
original item remains.

**Why:** HearthLedger is a balance tracker with no external connections by design; a sync
provider would require an API integration and credential handling, mirroring the real
estate valuation provider pattern.

**Cons:** External API integration, credentials, and a scheduled sync task. Significant
scope; out of scope for v1's no-connections stance.

**Context:** Positions rollup built over the existing `investment_lot` (cost-basis) data
with a new `asset_class` column (migration 0009), a `GET /investment-positions` endpoint,
and an `InvestmentPositionsPanel` on the Investments page.

**Depends on:** Positions rollup (done).

---

### Tax-estimate engine — remaining scope (broader state coverage, itemized deductions)

**What:** Two follow-ons now that the federal engine is complete and the four modeled states (CA/NY/GA/IL) have brackets + retirement-income exclusions: (1) expand state coverage beyond CA/NY/GA/IL toward all taxing states — including each new state's own retirement-income exclusion where it has one (the `STATE_RETIREMENT_EXCLUSION` config + `retirement_exclusion()` engine extend directly); (2) itemized-deduction support (Schedule A), which would let the AMT SALT add-back be exact rather than a planning input (today the regular-tax baseline always uses the standard deduction).

**Why:** Federal and the four demo-relevant states are feature-complete. The main remaining gap is breadth: only four states are modeled, so a household in any other taxing state gets a "not yet modeled" note.

**Cons:** State brackets (and per-state retirement exclusions) for the remaining ~37 taxing states are a large annual-maintenance surface — keep the isolate-and-cite discipline in `state_tax_tables.py` (one cited source per year). Itemized deductions are a meaningful new modeling layer (Schedule A), out of scope for a quick win.

**Depends on:** State tax engine + NIIT + AMT + state retirement exclusions, all shipped 2026-06-29/30; `state_tax_tables.py` extends directly.

---

## Completed

### User-scoped query keys — harden against cross-account cache bleed (P3, defensive)

**Completed:** v0.23.18.0 (2026-06-30, branch `feat/user-scoped-query-keys`) — Closed
the cross-account cache-bleed gap with the centralized identity-transition guard
(the TODO's option (b)), chosen over per-query-key scoping (option (a)) because
scoping would touch 50+ call sites and stay fragile to a forgotten prefix. New
`frontend/src/lib/sessionCache.ts`: `syncSessionCache(token)` decodes the JWT `sub`,
tracks the current identity, and calls `queryClient.clear()` only on a transition to
a _different_ non-null subject. Wired into `setAccessToken` — the single chokepoint
every token assignment passes through — so cache isolation no longer depends on each
flow remembering to clear, closing the "swap the token without routing through
`logout`" gap. Deliberate non-clears: same-subject refresh (no thrash; silent refresh
also bypasses `setAccessToken`) and "no user → user" login (nothing to leak; login
follows a cache-clearing logout). A "user → no user" logout transition does clear,
backstopping the explicit `queryClient.clear()` in `useAuth.logout` / `clearAuth`
(kept as defense in depth). No backend change, no migration, no behavior change for
current flows. Tests: 5 unit (`sessionCache.test.ts`).

### State retirement-income exclusions — IL/GA/NY (Tax-estimate engine)

**Completed:** v0.23.17.0 (2026-06-30, branch `feat/state-retirement-exclusions`) —
The state income-tax estimate now excludes retirement income (pensions + RMDs) for
the three modeled states that offer it: Illinois (full, no age gate), Georgia
(age-tiered $35k at 62-64 / $65k at 65+), and New York ($20k at 59½, modeled as
60+). New pure `state_tax.retirement_exclusion(state, member_ages, retirement_income)`
sums each member's per-taxpayer cap for the highest age tier they meet (so a married
couple where both qualify gets the doubled cap), capped at the household's retirement
income; IL excludes the full amount regardless of age. Config in
`state_tax_tables.STATE_RETIREMENT_EXCLUSION` (`RetirementExclusion` NamedTuple).
`estimate_state_tax` gained `retirement_income` + `member_ages` params and a
`retirement_exclusion` field on `StateTaxEstimate`; `report.py` passes pension + RMD
and queries active members' ages. No migration (reuses `households.state` + member
DOBs). Documented simplifications: pension + RMD only (not GA's broader investment
income); NY 59½ → 60+; NY government-pension full exclusion not distinguished;
age-gated state with no member DOB gets no exclusion (IL still applies). CA has no
exclusion. Tests: 8 engine unit + report integration (GA retiree, $65k excluded →
$1,239.70) + frontend (exclusion line renders).

### AMT preference inputs — SALT + ISO (Tax-estimate engine)

**Completed:** v0.23.16.0 (2026-06-29, branch `feat/amt-preference-inputs`) — Gave the
AMT engine real data to work with. Migration `0020` adds two nullable `NUMERIC(18,4)`
household columns (`amt_salt_preference`, `amt_iso_preference`); they are exposed on
`HouseholdResponse` / `HouseholdUpdate` (primary-only PATCH, `model_fields_set` clear,
non-negative validator) and entered on the Settings → Household & tax page as two
currency inputs with help text. `report.py` sums them into the `amt_preference_income`
it passes to `estimate_federal_tax`, so the Cash Flow AMT line now binds when a
household supplies preferences. Documented caveat surfaced in the UI: the SALT add-back
is only a real AMT item when itemizing, but the estimate uses the standard deduction, so
the inputs are planning estimates. Remaining tax scope (see open item): broader state
coverage + state retirement-income exclusions + optional itemized deductions. Tests:
household integration (set/clear/reject-negative) + report integration (AMT binds to
$44,527 with preferences, $0 without) + frontend (saves the inputs).

### Federal Alternative Minimum Tax (Tax-estimate engine)

**Completed:** v0.23.15.0 (2026-06-29, branch `feat/amt-estimate`) — Added the §55
AMT to the federal tax engine. New pure `tax.alternative_minimum_tax()` computes the
tentative minimum tax (26%/28% over the year-keyed exemption, which phases out at high
income) and owes `max(0, TMT - regular_tax)`; long-term capital gains / qualified
dividends keep their preferential rates on the ordinary AMT base. Cited 2025/2026
constants in `tax_tables.py` (IRS Rev. Proc. 2024-40 / 2025-32 via Tax Foundation),
including the OBBBA 2026 change that cut the exemption phaseout thresholds to
$500k/$1M and accelerated the phaseout rate from 25% to 50%. `estimate_federal_tax()`
gained an optional `amt_preference_income` input (default 0) and a new
`alternative_minimum_tax` field on `FederalTaxEstimate`, netted from after-tax income;
the cash-flow panel renders an AMT line gated on `> 0`. Honest limitation: with only
the standard-deduction add-back (no tracked preference items), AMT never exceeds the
regular tax under the high TCJA exemptions, so the live line is effectively always $0
— the engine is correct and tested with binding cases via the preference input, but
needs a preference-item data source to bind (see open item). No migration. Tests: 4
engine unit + 2 integration + AMT-line assertions on the cash-flow panel test.

### State income tax estimate + federal NIIT (Tax-estimate engine)

**Completed:** v0.23.14.0 (2026-06-29, branch `feat/state-tax-estimate`) — The Cash
Flow report now estimates state income tax and the §1411 net investment income tax
alongside the federal income tax. New `app/services/state_tax.py` +
`state_tax_tables.py` mirror the federal `tax.py` / `tax_tables.py` split: data-only,
year-keyed, cited (Tax Foundation 2025 via `/browse`), pure functions returning a
`StateTaxEstimate`. `estimate_state_tax()` is keyed off `households.state` and always
returns an estimate — a modeled taxing state (CA/NY/GA/IL, full brackets + standard
deduction), a real $0 for the eight no-income-tax states, or `modeled=False` + note
for any other state. NIIT (3.8% on the lesser of net investment income and MAGI over
a statutory threshold) is added to the federal engine as `net_investment_income_tax()`
and a new field on `FederalTaxEstimate`, netted from after-tax income but kept out of
the income-tax effective rate. `report.py` derives both estimates from one household
fetch and surfaces them on `CashFlowReport`; the Cash Flow page renders a state-tax
line and a NIIT line. No migration (`state` / `filing_status` exist since 0018).
Documented simplifications: states tax qualified income as ordinary, SS excluded,
HoH/MFS → single schedule, QSS → MFJ, retirement-income exclusions not applied.
Remaining (see open item): AMT + broader state coverage + retirement-income exclusions.
Tests: 13 state-engine unit + 5 NIIT engine unit + 1 report integration + 2 frontend.

### DESIGN.md — HearthLedger design system document

**Completed:** 2026-06-29 (branch `docs/design-system-md`) — Added `DESIGN.md` at
the repo root, extracted from the code rather than the original TODO's hints
(which were stale: the shipped accent is green via Hearth CSS variables, not
indigo-600, and Archivo — not Spectral — is the body font; Spectral 600 is the
brand wordmark only). Documents the color/text/accent token set in `index.css`
(dark-default + light), typography + type scale, the spacing/radius scale, the
`AppLayout` shell (214px sidebar, nav, segmented range toggle), and the canonical
`components/ui/` primitives (`SectionHeader`, `DataCard`, `DataRow`). Honestly
flags the live two-system drift (Hearth tokens vs ad-hoc indigo-600/gray-200/
bg-white in reports/forms), the dark-only `@theme` limitation, the two modal
patterns, and vestigial `App.css`, with convergence guidance. Linked from the
docs index; auto-read by the gstack design-review tooling at repo root.

### Custom date mode for the Spending Report (cash-flow drill-down range)

**Completed:** 2026-06-25 (branch `feat/spending-custom-date-mode`) — Closes the
D2-eng follow-on from the cash-flow-categories plan. The Spending Report gained a
"Custom" preset with from/to date inputs (alongside this_month / 3m / 6m / 12m), and
the route's `validateSearch` now accepts `from`/`to`. A `from`+`to` pair in the URL
opens the report in Custom mode on that exact range. The Cash Flow → Spending
drill-down (both the per-category bars and the "View full breakdown" link) now carries
the cash-flow panel's current date range into the search, so the drilled report lands
on the matching range, not just the matching category. An inverted range (from > to)
shows a warning and skips the query. Tests: 3 added to ReportSpending (opens on URL
range, refetch on input change, inverted-range guard) + 1 to ReportCashFlow (drill-down
carries the range).

### Roth-conversion-ladder analysis — multi-year gap-year projection (Identity layer)

**Completed:** 2026-06-25 (branch `feat/roth-conversion-ladder`) — Models the
standard Roth-conversion ladder over the FIRE gap years (retirement age → RMD
start age): each year converts pretax→Roth up to the top of a chosen federal
bracket (the strategy, fill-to-target-bracket), shrinking the pretax balance so
future RMDs and the tax on them fall. Built as a **standalone analysis** (the FIRE
projection itself stops at the accumulation FIRE year, so the gap/drawdown years
aren't in its window): a pure, DB-free `app/services/roth_ladder.py` simulates a
single pretax bucket plus per-year ordinary/SS income, runs it **with vs. without**
conversions to a horizon (default age 90), and reports lifetime federal tax saved.
New `tax.bracket_ceiling_for_rate()` (top of a target bracket); the conversion
correctly accounts for the standard-deduction slack so taxable income lands on the
bracket ceiling. Endpoint `GET /fire-scenarios/{id}/roth-ladder?ceiling_rate=&retirement_age=&horizon_age=`
(query-param driven, interactively explorable, no migration); gates with a `note`
when filing status / DOB / pretax balance is missing. The FireDetail page gained a
"Roth conversion ladder" section with a target-bracket selector, gap-year table, and
a lifetime-tax-saved (or -cost) headline. Notably the model is honest: with no
growth and low other income it shows conversions can _cost_ lifetime tax (RMDs would
stay in lower brackets), not just save. Scope: federal only, ignores state tax and
the second-order SS-provisional feedback of a conversion. Tests: 6 pure-sim unit
(fills to ceiling, deduction-aware amount, saves-with-growth, costs-without-growth,
income reduces room, no gap years) + 3 integration (422 validation, unavailable
gating, available schedule) + 4 frontend (headline, cost framing, note, bracket
refetch).

### Full-household-income tax basis + preferential cap-gains/QD rates (Identity layer)

**Completed:** 2026-06-25 (branch `feat/tax-full-income-basis`) — Broadened the
federal tax-estimate engine from a retirement-income-only basis to the household's
full taxable income. `tax_tables.py` gained the year-keyed long-term capital-gains /
qualified-dividend rate breakpoints (0/15/20%, 2025 + 2026, all filing statuses;
verified via published IRS Rev. Proc. figures). `tax.py` gained `preferential_tax()`
(qualified income stacked on top of ordinary taxable income, taxed at the
preferential schedule) and `estimate_federal_tax()` now takes a `qualified_income`
component; capital gains/dividends also count toward §86 provisional income. The
cash-flow report classifies every income category by tax treatment (ordinary /
qualified / Social Security / excluded) and feeds the full basis in; the estimate
moved from `RetirementIncomeBreakdown` to a top-level `CashFlowReport.federal_tax_estimate`
so it now surfaces for wage-earners with no retirement income, not just retirees, in
its own "Estimated federal tax" panel (with a preferential-rate line when qualified
income is present). Two documented estimate simplifications: `capital_gains` is
treated as long-term and `dividends` as qualified. Remaining (see open item): state
tax + AMT/NIIT. Tests: 4 engine unit (preferential stacking across 0/15/20, QD raising
taxable SS, qualified-income preferential rate, zero-default backward compat) + report
unit (full-income basis surfaces for a wage earner) + 1 frontend (wage-earner panel +
preferential line).

### Social Security claiming plan feeds FIRE projections (Identity layer)

**Completed:** 2026-06-25 (branch `feat/ss-fire-integration`) — Closes the loop
from the claiming-age engine into FIRE. Added `household_members.ss_monthly_benefit_at_fra`
(PIA) + `ss_claiming_age` (migration 0019), exposed on the member create/update/
response schemas (validated: benefit ≥ 0, age 62-70, clearable via
`model_fields_set`). The Profile "Social Security claiming" section now persists
both and highlights the chosen age in the table. `FireScenarioService.project()`
derives a `social_security` income stream from the target member's saved plan
(PIA adjusted for claiming age, starting the year they reach it) and supersedes
any manual SS stream so it's never double-counted. Tests: 2 FIRE-projection unit
(stream appears at the claiming year; manual stream superseded) + member-field
coverage + 1 frontend (save).

### Social Security claiming-age benefit adjustment (Identity layer)

**Completed:** 2026-06-25 (branch `feat/ss-claiming-age`) — Benefit-adjustment
engine (`app/services/social_security.py`): given a member's PIA (FRA benefit
estimate) and date of birth, computes the benefit at each whole claiming age
62-70 — early reduction (5/9 of 1%/mo for the first 36 months, 5/12 beyond) and
delayed-retirement credit (2/3 of 1%/mo to 70), with FRA-by-birth-year from the
existing `age.py`. Endpoint `GET /members/{id}/social-security-estimate?
monthly_benefit_at_fra=` returns the comparison; a calculator on the Profile page
shows the table (monthly/annual/% of FRA, FRA row flagged). Remaining (see open
item): persist PIA + claiming age and feed the adjusted benefit into FIRE
supplemental income. Tests: 6 engine unit (FRA-67 at 62 → 70%, at 70 → 124%; FRA
66y2m) + 3 integration (estimate / no-DOB 400 / negative 422) + 2 frontend.

### Roth-conversion bracket headroom — first slice (Identity layer)

**Completed:** 2026-06-25 (branch `feat/roth-conversion-bracket-headroom`) — The
core Roth-conversion planning primitive, built on the federal tax engine:
`bracket_headroom()` returns how much more ordinary income (a pretax → Roth
conversion) fits before crossing into the next federal bracket, plus that next
bracket's rate. Surfaced as `roth_conversion_room` + `next_bracket_rate` on
`FederalTaxEstimate`, shown on the Cash Flow retirement panel ("Roth conversion
room: $X can be converted before the Y% bracket") when there's headroom. Remaining
(see open item): the multi-year conversion projection across the FIRE drawdown.
Tests: 3 engine unit (headroom in/at-threshold/top-bracket + MFJ retiree room
34,450) + 1 frontend (room shown; omitted in top bracket).

### Federal tax-estimate engine — first slice (Identity layer)

**Completed:** 2026-06-25 (branch `feat/identity-filing-status-state`) — Federal
income-tax estimate: ordinary-income brackets + standard deduction + §86 Social
Security provisional-income taxation, year-keyed for 2025 + 2026. Constants verified
against IRS Rev. Proc. / OBBBA via `/browse` and isolated in
`app/services/tax_tables.py` (cite + update annually). Pure functions in
`app/services/tax.py` return a `FederalTaxEstimate`. Surfaced on the Cash Flow
report's retirement-income panel (est. federal tax + after-tax + marginal rate) when
the household has a filing status, using pension + RMD as ordinary income and the SS
bucket. Deferred to the remaining-scope item: state tax, full-household-income basis
(currently retirement-income only), preferential cap-gains / qualified-dividend
rates, AMT / NIIT. Tests: 12 engine unit (hand-computed bracket math + SS tiers) + 2
report + 1 frontend.

### Filing status + state of residence attributes (Identity layer — foundational)

**Completed:** 2026-06-25 (branch `feat/identity-filing-status-state`, stacked on
the Budgets branch) — Added two nullable household-level identity columns
(migration `0018`): `filing_status` (PG enum: single / MFJ / MFS / HoH / QSS) and
`state` (two-letter US/DC code, app-validated and uppercased). Exposed on
`HouseholdResponse`/`HouseholdUpdate` (PATCH `/household`, primary-only, uses
`model_fields_set` so explicit nulls clear them) and a new **Household & tax**
settings page (`/settings/household`) with a primary-only edit form + read-only
view for other members. Landed ahead of their consumer per the chosen sequencing
(foundational attrs first); no report reads them yet — the federal/state
tax-estimate engine is the next item. Tests: 6 backend integration (set/clear/
validate/primary-only/partial-update) + 5 frontend.

### Quarterly budget period — Budgets tab

**Completed:** 2026-06-25 (branch `feat/budgets-quarterly-persistence-constraint`) —
Added `"quarterly"` to the `budget_period` enum (migration `0016`, `ALTER TYPE ...
ADD VALUE`), threaded it through the model, Pydantic schemas (`BudgetPeriod` in
`schemas/budget.py` and `schemas/report.py`), and the budget-vs-actuals report,
which now prorates quarterly budgets to monthly (÷3) alongside the existing annual
(÷12). The Budgets UI gained a quarterly radio, a "Quarterly amount" label, a "÷3
per month" proration note, a `/qtr` row suffix with monthly-equivalent hint, and a
`quarterly÷3` actuals badge. Unit test asserts the ÷3 report proration.

### Sort/filter state persistence — Budgets tab

**Completed:** 2026-06-25 (branch `feat/budgets-quarterly-persistence-constraint`) —
The Budget vs Actuals and All Budgets sort selections now persist to `localStorage`
(`hl.budgets.actualsSort` / `hl.budgets.budgetsSort`). Stored values are validated
against the allowed sort set on read, so a renamed/removed option falls back to the
default rather than sticking (addresses the "stale stored values" caveat). Writes
are wrapped so private-mode/SSR localStorage failures degrade gracefully. Vitest
covers persist-on-change, restore-on-mount, and invalid-value fallback.

### Unique constraint on (household_id, category_id, effective_from) in budgets

**Completed:** 2026-06-25 (branch `feat/budgets-quarterly-persistence-constraint`) —
Migration `0017` adds the unique constraint
(`uq_budgets_household_category_effective_from`) after a defensive dedup pass that
keeps the newest row per natural key (behavior-preserving, since the report already
treats later rows as authoritative). `BudgetService.create`/`update` now pre-check
the natural key and raise 409 on conflict, so duplicates surface as a clean error
instead of a raw IntegrityError 500. Unit tests cover create-conflict and
update-into-conflict.

### Batch prior-year snapshot reads in the RMD engine (Identity layer E4)

**Completed:** v0.23.3.0 (2026-06-25) — Replaced the per-account snapshot
lookup in `RmdService` with a single keyed `DISTINCT ON (account_id)` query
(`_batch_prior_year_snapshots`) across every pretax account in the report, then
a pure in-memory sum (`_sum_prior_year_balances`) per member — mirroring the
batched-balance pattern in `account.py`. `_member_rmd` is now synchronous (no
per-member DB calls). Tests assert the batched total/latest-date matches the old
per-account loop, including multi-account and multi-member cases.

### Structured logging in the RMD engine (Identity layer T12)

**Completed:** v0.23.3.0 (2026-06-25) — `RmdService` now emits an info log per
member: the computed line (member, attained age, pretax base, snapshot date,
divisor, RMD) plus the three "$0" reasons (no date of birth, below start age, no
prior-year balance), so a "why is my RMD $0" question is reconstructable from
logs. Covered by `caplog` tests.

### Member retirement target age (Identity layer)

**Completed:** v0.23.0.0 (2026-06-24) — Added `household_members.retirement_target_age`
(nullable smallint, migration 0015), exposed it on the member create/update/response
schemas (validated 18–100, clearable via `model_fields_set`), and added a "Target
retirement age" field to the self-service Profile page and the Members admin drawer.
Made load-bearing by the milestone timeline: `age.milestones()` now emits a "Target
retirement" event at `dob + retirement_target_age` when set. The FIRE
accumulation→withdrawal consumer was deliberately deferred — FIRE already has its own
scenario-level `target_retirement_age`, so wiring a member-level default into it needs
its own design rather than overlapping the existing field.

### Age-milestone timeline UI (Identity layer T10)

**Completed:** v0.21.0.0 (2026-06-24, PR #61) — Added a "Retirement Milestones"
report (`/reports/milestones`) rendering each member's forward-looking timeline:
59½ penalty-free withdrawals, Social Security earliest (62) and full retirement
age (FRA-by-birth-year lookup added to `app/services/age.py`), Medicare (65), and
RMD start. New `app/services/milestone.py` + `GET /reports/age-milestones`.
Reached milestones are dimmed; the next upcoming one is badged; no-DOB members get
a prompt. (Documented in CHANGELOG under 0.21.0.0 retroactively.)

### Wire RMD into FIRE projections (Identity layer T9)

**Completed:** v0.21.0.0 (2026-06-24, PR #60) — FIRE projections now draw each
member's required minimum distribution from their pretax balance once they reach
RMD age; `YearProjectionResponse` gained `required_distribution` and the FIRE
detail table shows a Required distribution column (hidden when no RMD applies in
the window). No-pretax / no-DOB members are a clean no-op. (Documented in CHANGELOG
under 0.21.0.0 retroactively.)

### Self-service profile page + self-or-primary DOB authz (Identity layer T8)

**Completed:** v0.22.0.0 (2026-06-24) — Added a "Your profile" page
(`/profile`, under the user dropdown) where any member edits their own display
name and date of birth. `MemberService.update` now allows self-or-primary edits
(CEO-review Decision 3); role and `is_active` mutations stay primary-only, so a
member can't self-promote or self-deactivate. Closes the one spot the identity
layer had diverged from an approved decision.

### Account tax-treatment override UI (Identity layer T6)

**Completed:** v0.22.0.0 (2026-06-24) — Exposed `tax_treatment` on the account
create/update/response schemas and added a "Tax treatment" select to the Edit
account dialog (pre-tax / roth / taxable / unset). `create` seeds the value from
the account type (mirrors migration 0014); `update` can correct or clear it via
`model_fields_set`. Accounts whose treatment isn't implied by type (generic IRA,
after-tax 401k, rollover) can now be corrected so their RMD is right.

### Include SBLOC/margin in transaction-tracked liability valuation

**Completed:** v0.20.1.0 (2026-06-24) — Added `sbloc` and `margin` to
`TXN_TRACKED_LIABILITY_TYPES` in `app/services/report.py`, so revolving credit
lines value from their running transaction sum and a Debt record can no longer
pin them to a static balance (the v0.19.0.0 flat-line bug). Preserved the
snapshot fallback by extending the transaction-tracked branch to txn → Debt →
snapshot → 0, which also gives credit cards / lines of credit / loans a snapshot
fallback they lacked. Behavior-neutral for the sample data (verified by the
per-household net-worth agreement test). Two regression tests added.

### Investment positions rollup — Top positions + Holdings mix

**Completed:** v0.15.0.0 (2026-06-22) — Cost-basis lots
now roll up into a per-ticker "Top positions" table and an asset-class "Holdings mix"
donut on the Investments page. Added `investment_lot.asset_class` (migration 0009), a
`GET /investment-positions` endpoint (`InvestmentLotService.positions_summary`), and
typed frontend panel. Seed lots are auto-classified by ticker for a meaningful demo mix.
Cost basis is used (no live prices). Optional brokerage sync remains deferred (above).

### Pension PV formula rework + historical estimate time-series

**Completed:** v0.15.0.0 (2026-06-22) — Replaced the
perpetuity (`annual / 0.04`) with a model that discounts deferred benefits over the years
to eligibility, models COLA growth as a growing annuity, values a finite life annuity, and
adds the survivor benefit. Centralized in `app/services/pension_valuation.py`; the report
layer and the net-worth UI now use the shared value (`PensionAnnotation.estimated_pv`).

Added `PensionEstimateHistory` (migration 0010): `PensionService` records an estimate
snapshot on create and whenever a PV-relevant field changes, and each net-worth point is
valued from the estimate in effect at that date (`pension_value_at` / `effective_estimate`).
Editing today's benefit estimate no longer rewrites historical chart points. Pensions
predating the table fall back to current fields; existing rows were backfilled in the
migration. This fully closes the original Phase 8 item.

### Retirement income breakdown in cash-flow report

**Completed:** v0.15.0.0 (2026-06-22) — The cash-flow
report now breaks retirement income into labeled buckets (Social Security / Pension /
RMDs) via `CashFlowReport.retirement_income`; the Cash flow page shows a panel that hides
itself when the household draws no retirement income. (Phase 11 CEO plan, Phase 12
candidate.)

### Assets.test.tsx — null-mortgage equity test

**Completed:** v0.15.0.0 (2026-06-22) — Added a Vitest
case covering a cash-purchased property (`linked_mortgage_account_id: null`,
`mortgage_balance_visible: false`): asserts the equity figure renders and no mortgage line
appears. Closes the Phase 11 §2.5 verification item.

### Context-aware category add buttons on Accounts page (Phase 8 F6)

**Completed:** v0.9.3.0 (2026-06-20) — Per-category "+" buttons on the Accounts page now use context-aware handlers: Banking & Cash opens the add modal filtered to banking types, Liabilities opens it filtered to liability types, and Retirement/Investments/Real estate navigate to their dedicated pages. Previously all "+" buttons opened the same modal, which showed no options for Retirement/Investment/Real estate categories.

### WeasyPrint macOS test skip

**Completed:** v0.9.2.0 (2026-06-20) — `test_phase_5.py` uses `ctypes.util.find_library("gobject-2.0")` to auto-detect library availability and marks PDF tests with `pytest.mark.skipif` when the library is absent. No manual platform flag needed.

### Fix RealEstateService.update() nullable pattern

**Completed:** v0.7.0.0 (2026-06-18) — `real_estate.py:update()` now uses `model_fields_set` iteration; `linked_mortgage_account_id` can be cleared to null.

### Extract snapshot query to AccountRepository

**Completed:** v0.7.0.0 (2026-06-18) — `AccountRepository.latest_snapshot(account_id)` returns `(balance, date)` tuple used by both equity endpoint and report service.
