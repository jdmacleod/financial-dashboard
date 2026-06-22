# HearthLedger — Critical Review of the Five-Household Demo Dataset
## Coverage analysis for households up to $20M net worth, with recommended enhancements

**Prepared:** June 21, 2026
**Reviews:** `hearthledger-demo-data-spec.md` (H1–H3) and `hearthledger-demo-data-spec-addendum.md` (H4–H5)
**Scope of this document:** Identify missing financial components and situations for the ≤ $20M net-worth band, ground the gaps in current (2026) wealth-management practice, and recommend specific additions, edge cases, and intentional omissions — with references and reasoning.

---

## 1. What the current five households do well

Before the critique, it is worth being precise about the strengths, because several of the recommendations below are about *depth* within an already-sensible structure rather than wholesale gaps.

The set spans roughly an 83× net-worth range ($154.5K → $12.86M) across five states, three of which (TX, TN, FL) have no state income tax, which gives genuine tax-structure diversity rather than cosmetic geographic spread. The lifecycle arc is deliberate and complete on the *time* axis: early-career renters (H4), dual-income accumulators (H1), a multi-generation family with a rental (H2), a high-income household at peak earning (H3), and a fully retired couple in decumulation (H5). The decumulation mechanics in H5 are the standout — the RMD transition at age 73 under SECURE 2.0, Medicare IRMAA tiering with the two-year income lookback, ACA Marketplace premiums for the pre-65 partner, an active Social Security claim, and a defined-benefit pension together exercise nearly the entire retirement-income surface that a tool in this band needs to model. Real-estate variety is also strong: owner-occupied, long-term rental, short-term/vacation rental, HELOC, pure renting, and an out-of-state second home.

The weaknesses are therefore not in the skeleton. They are concentrated in four areas that matter disproportionately for the $3M–$20M band: **equity compensation and concentrated positions, wealth-transfer structure, risk-management/insurance as balance-sheet items, and charitable vehicles.** These are precisely the pillars that separate a "mass-affluent budgeting app" from a "household finance system that holds up at $10M+." Below I organize the analysis around the standard wealth-management planning pillars, map current coverage, then go gap by gap.

---

## 2. The organizing framework: ten planning pillars for ≤ $20M, and how the current set maps

Wealth-management practice for this band is conventionally organized around ten pillars. Mapping the five households against them exposes where coverage is thin (✓ = represented and reasonably deep; ~ = touched but shallow; ✗ = absent):

| # | Planning pillar | H1 | H2 | H3 | H4 | H5 | Overall |
|---|---|---|---|---|---|---|---|
| 1 | Cash flow & budgeting | ✓ | ✓ | ✓ | ✓ | ✓ | **Strong** |
| 2 | Investment management & **asset allocation / concentration** | ~ | ~ | ~ | ~ | ~ | **Shallow** |
| 3 | Income, capital-gains & multi-year **tax planning** | ~ | ~ | ~ | ~ | ✓ | **Mixed** |
| 4 | Retirement / decumulation | ~ | ~ | ~ | ~ | ✓ | **Strong (via H5)** |
| 5 | **Estate & wealth transfer** (trusts, gifting, GST) | ✗ | ✗ | ✗ | ✗ | ✗ | **Absent** |
| 6 | **Risk management & insurance** (umbrella, life as asset, DI, LTC, specialty) | ✗ | ✗ | ~ | ✗ | ~ | **Absent/expense-only** |
| 7 | **Charitable / philanthropic** (DAF, CRT, QCD) | ✗ | ✗ | ✗ | ✗ | ✗ | **Absent** |
| 8 | Education funding | — | ~ | ~ | — | — | **Shallow** |
| 9 | **Equity compensation** (RSU/ISO/NSO/ESPP) | ✗ | ✗ | ✗ | ✗ | ✗ | **Absent** |
| 10 | Business / closely-held interests | ✗ | ~ | ✓ | ✗ | ✓ | **Partial** |

The pattern is clear: pillars 1 and 4 are well served, but pillars **5, 6, 7, and 9 — estate transfer, insurance-as-asset, charitable vehicles, and equity compensation — are essentially empty across all five households**, and pillar 2's concentration/cost-basis dimension is missing everywhere. For the net-worth band the tool targets, those four are not edge features; they are the core of what a $5M–$20M household's advisor spends time on. The remainder of this review is mostly about filling those four, plus closing the $13M–$20M net-worth gap and adding realism to income and life-transition modeling.

---

## 3. Major gaps, in priority order

### 3.1 Equity compensation and concentrated single-stock positions — the largest gap

No household holds RSUs, ISOs, NSOs, or ESPP shares, and none models a concentrated single-stock position. For the wealth band in question this is the single most consequential omission, for two reasons.

First, equity compensation is the dominant wealth-*building* mechanism for the $3M–$15M band in technology, biotech, finance, and entertainment. Industry guidance repeatedly notes that executives commonly accumulate 50–80% of net worth in employer stock through a mix of options, RSUs, ESPP, and direct holdings, and that a position crossing roughly 10–25% of net worth is the threshold at which a deliberate diversification strategy becomes necessary (U.S. Bank; Carter Financial). Given that you are based in LA media/entertainment, a household whose wealth is built on vested equity is arguably *more* representative of your likely user base than the consulting-LLC structure currently given to H3.

Second, equity compensation is the richest source of the kinds of transaction and reporting patterns HearthLedger is built to surface. It introduces: lumpy, non-monotonic income (a vest event drops a large taxable sum into a single month); supplemental withholding that is frequently set at the flat 22% federal rate and under-withholds for high earners, producing an "April problem" (RHA Wealth; True Wealth Design); AMT exposure from the bargain element on ISOs exercised and held; the 83(b) election timing decision; sell-to-cover share withholding; and 10b5-1 pre-scheduled selling plans used to diversify out of concentration without insider-trading exposure (Brady Ware; Foley Hillsley/Baird). A concentrated position also drives cost-basis/lot tracking and tax-loss harvesting against the gains realized on systematic sales.

**Recommendation:** Give H3 (Brentwood, peak-earning) a primary equity-compensation profile — quarterly RSU vests with sell-to-cover, an ISO grant with a held tranche that generates an AMT event in one tax year, and a resulting concentrated position in one employer's stock representing ~30% of the investment portfolio. Add a 10b5-1-style scheduled-sale pattern that systematically trims the position over the 30-month window. This single change exercises pillar 2 (concentration), pillar 3 (AMT, multi-year timing), and pillar 9 simultaneously, and produces the most "demo-worthy" net-worth and cash-flow time series in the dataset. A lighter version belongs in H1 or H4 as well (a single ESPP at a 15% discount with a lookback), since ESPP is common far below the HNW line.

*Note on the v2 gross-salary deferral:* the spec deferred pre-tax/payroll-deduction tracking to v2. That constrains modeling of withholding *detail*, but it does not block modeling vest *events* and the resulting *position* at net values, which is where most of the demo value sits. Flag the withholding nuance as a v2 enrichment rather than a blocker.

### 3.2 Estate and wealth-transfer structure — absent, and the state-tax dimension is mis-targeted

No household has a trust of any kind, and no account carries a title/ownership structure beyond individual or joint. Two distinct issues follow.

**(a) The federal picture changed in 2025 and the dataset should reflect the new reality.** The One Big Beautiful Bill Act, signed July 4, 2025, made the federal estate, gift, and GST exemption a *permanent* $15M per person / $30M per married couple effective January 1, 2026, indexed for inflation from 2027 — replacing the scheduled sunset to roughly $7M that dominated planning conversations through 2024–2025 (Pierce Atwood; Morgan Lewis; IRS Rev. Proc. 2025-32). The practical consequence for your band: a *married couple* under $30M (which includes every household in the set) now has essentially no federal estate exposure, so the interesting estate-planning content shifts to (i) *single* individuals approaching the $15M line, and (ii) *state* estate/inheritance taxes, which were untouched by OBBBA and have far lower thresholds.

**(b) The state-tax edge case is already sitting in H2 but is not exploited.** H2 lives in **Naperville, Illinois** with a ~$3.4M net worth. Illinois imposes its own estate tax with a **$4M per-person exemption that is not indexed for inflation and — critically — not portable between spouses**, with graduated rates up to 16% and a "cliff" structure in which crossing the threshold taxes the estate from the bottom rather than only the excess (Illinois Attorney General Form 700 fact sheet; Faegre Drinker; Lechner Law, June 2026). A bill to raise it to $8M (HB2601) was proposed but had not passed as of mid-2026 (JRC Insurance Group). H2 is therefore the *perfect* vehicle to demonstrate that a household with zero federal estate exposure can still face real state estate liability — and the non-portability point means a credit-shelter/bypass trust is the standard mitigation. Currently the dataset under-represents state estate tax: H3 (CA) and H5 (FL) sit in states with no estate tax, and TX/TN have none either, so the one household positioned to surface this (H2 in IL) doesn't lean into it.

**Recommendation:** Introduce a revocable living trust as an account/asset *titling* layer for H3 and H5 (this is standard at $9M+ and exercises the ownership and RBAC model without requiring new tax logic). Separately, encode H2's Illinois state-estate-tax exposure as a documented planning note and, if the data model supports it, a bypass-trust titling on a portion of assets. If you want to demonstrate *federal* estate planning at the exemption boundary, that argues for the new single-filer household in §4 rather than stretching any couple, since couples are now sheltered to $30M.

*Data-model implication:* this gap is partly structural, not just seed data. A `trust`/`ownership_entity` concept and an account `title`/`ownership_structure` field would be needed to represent revocable trusts, bypass trusts, and (later) irrevocable vehicles. Worth a schema note even if v1 only populates revocable-trust titling.

### 3.3 Charitable giving vehicles — absent, and two households are textbook candidates

No donor-advised fund (DAF), charitable remainder trust (CRT), qualified charitable distribution (QCD), or private foundation appears anywhere. Two households are textbook fits, and adding them exercises an entire category of accounts and transactions:

- **H5 (retired, $12.86M, past RMD age) and the QCD.** A retiree subject to RMDs can direct up to an inflation-indexed limit (about $108K in 2025) from an IRA straight to charity as a Qualified Charitable Distribution, satisfying the RMD while excluding the amount from income — which also helps manage the very Medicare IRMAA tiers H5 already models. (Note a QCD cannot go to a DAF — a nice rule to encode correctly.) This is a clean, instructive interaction between two features H5 already has.
- **H3 (high income, appreciated/concentrated stock) and the DAF.** Contributing appreciated shares to a DAF gives an immediate deduction (subject to the 30%-of-AGI limit for long-term appreciated non-cash gifts; 60% for cash), avoids capital-gains tax on the donated shares, and lets grants be timed independently of the deduction (Fidelity Charitable; Slowik Estate Planning). This pairs naturally with the equity-comp/concentration profile recommended in §3.1 — donating appreciated company stock is a primary diversification-with-tax-benefit move.

A CRT is a reasonable stretch goal for the new high-net-worth single-filer household (§4): fund with a low-basis appreciated asset, take a partial deduction on the present value of the remainder, receive a lifetime income stream taxed under the four-tier rules, and name a DAF as the remainder beneficiary for flexibility (Fidelity Charitable; Pinellas Community Foundation). One current wrinkle worth a documentation note: OBBBA introduced, effective 2026, a 0.5%-of-AGI floor and a 35% cap on the benefit of itemized charitable deductions for top-bracket taxpayers (Slowik Estate Planning) — so the deduction modeling should not assume dollar-for-dollar benefit at the top rate.

**Recommendation:** Add a DAF account + appreciated-stock contribution transactions to H3, and a QCD pattern to H5. Treat a CRT as optional and attach it to the §4 household.

### 3.4 Insurance and risk management — modeled only as an expense line, never as a balance-sheet item

Life insurance appears only as a *budget expense* (H3's `life_insurance` line). For the target band this materially understates the role insurance plays, in two ways.

**(a) Umbrella liability is missing entirely and is close to mandatory above ~$1M net worth.** Standard guidance is to carry umbrella coverage at least equal to net worth, with $5M–$25M typical for affluent households, at strikingly low cost (often a few hundred dollars per additional $1M) (Carter Financial; Wheeler & Taylor; MAI Capital). It is one of the most cost-efficient risk tools in the entire plan, and any household above H1's level that lacks it is unrealistic. It belongs on H1, H2, H3, and H5 as a modest recurring premium plus a coverage-metadata record. The STR in H3 and the rental in H2 raise the liability rationale further.

**(b) Cash-value life insurance is a balance-sheet asset, not just an expense.** Permanent policies (whole, universal, IUL) accumulate cash value that is genuinely part of net worth and can be borrowed against; in estate contexts an ILIT holds the policy to keep the death benefit out of the taxable estate and to provide liquidity to pay estate tax or equalize inheritances (EP Wealth; Trusts & Estates). For a household-finance tracker, a cash-value policy is the cleanest example of an insurance product that needs to appear as an *asset* with a growing balance — a feature the current dataset never exercises. This is a strong fit for H5 (estate liquidity / wealth transfer) or the §4 single-filer.

Two further coverages round out the pillar and have cash-flow (not balance-sheet) implications: **disability insurance**, essential for the income-dependent earners in H1/H3/H4, and **long-term-care insurance**, a standard pre-retirement consideration for H2 and a near-term reality for H5's cohort. And given your own wine-curation interest, **scheduled/specialty coverage** for collectibles (fine art, jewelry, wine) is a realistic and on-brand addition for H3 or H5 — it also pairs with treating a wine collection as a tracked alternative asset (§3.7).

*Data-model implication:* an `insurance_policy` entity that can simultaneously (i) carry coverage metadata, (ii) post a recurring premium expense, and (iii) for permanent policies, hold a cash-value balance as an asset, would cover umbrella, term, permanent, DI, LTC, and specialty in one structure.

### 3.5 Advanced retirement-savings mechanics — the accumulation side is plain-vanilla

H5 covers decumulation thoroughly, but the *accumulation* households use only straightforward Traditional/Roth 401(k), IRA, SEP-IRA, and HSA contributions. Several mechanisms that are bread-and-butter for high earners and for retirees in the pre-RMD window are absent:

- **Backdoor Roth** (non-deductible IRA → Roth conversion) for H3, who is over the direct-Roth income limit.
- **Mega-backdoor Roth** (after-tax 401(k) contributions converted in-plan) — relevant wherever a plan allows it; a good fit for H1 or H4 if their employer plans support it.
- **The Roth-conversion window** — H5's most glaring omission on the planning side. A retiree in the low-income years *between* retirement and RMD onset typically executes partial Roth conversions to fill up lower brackets before RMDs and Social Security push income (and IRMAA tiers) higher. H5 already models the RMD transition; layering pre-2025 conversion activity into the 2024 data would make the before/after story far richer and is highly realistic.
- **Inherited IRA under the SECURE Act 10-year rule** — a common situation (a non-spouse beneficiary must draw the account down within ten years, with annual RMDs in many cases). This is a distinctive account type with its own drawdown pattern and is currently unrepresented.

**Recommendation:** Add a backdoor Roth to H3, a Roth-conversion-window pattern to H5's 2024 history, and consider an inherited IRA on the §4 household (a natural fit if that household recently lost a parent).

### 3.6 Cash and fixed-income management beyond checking/savings

Every household's liquidity is modeled as checking + savings. Real households in this band hold meaningful cash in **money-market funds, T-bills, CDs, I-bonds, or short bond ladders** for yield and safety, and the high-net-worth households often run a **securities-based line of credit (SBLOC)** to fund large expenses without triggering taxable sales (True Root Financial describes exactly this pattern for funding college from a concentrated position). None of this appears. Adding a T-bill ladder or MMF sweep to H3/H5 and an SBLOC to H3 would exercise account types and a borrowing pattern the current set misses, and the SBLOC pairs naturally with the concentration profile in §3.1.

### 3.7 Alternative and private assets — none represented

There are no private-equity/VC fund commitments, angel investments, private credit, crypto/digital assets, or tracked collectibles. Two of these are worth adding for both realism and feature coverage:

- **A private-fund commitment with capital calls** (for H3 or the §4 household) introduces a genuinely distinctive cash-flow pattern: an outstanding *committed* amount drawn down via irregular capital calls over time, against which distributions later flow back. Nothing else in the dataset produces that shape, and it is a defining feature of HNW portfolios — to the point that illiquidity from PE/VC commitments is now a recognized estate-*liquidity* problem that drives life-insurance planning (Trusts & Estates).
- **A tracked collectible asset** — a wine collection is the obvious candidate given your domain — exercises a manually-valued, appreciating, non-financial asset with associated specialty insurance (§3.4) and is a memorable demo element.

Crypto is a reasonable optional addition (it is just another manually-or-API-valued asset class), though it can be flagged as lower priority.

### 3.8 Life-transition / discontinuity events — the time series is too smooth

All five households read as steady accumulation or steady decumulation. The transaction generator likely produces near-monotonic monthly patterns. Real financial histories — and the most compelling demos of net-worth, cash-flow, and budget-variance reporting — contain discontinuities. None of the following is represented, and each produces a distinctive, instructive pattern:

- A **job loss / unemployment gap** with a corresponding income stop and spend-down (fits H1 or H4).
- A **market drawdown** reflected in investment valuations (a 2024–2025 dip and recovery in the snapshot series), so the net-worth chart isn't a straight line up.
- A **liquidity event** — business sale, IPO/lockup expiration, or large bonus — producing a one-time cash infusion and a tax spike (pairs with H3's equity comp).
- An **inheritance** event (a step-up-in-basis asset arriving), which is also the natural origin story for the §4 single-filer's wealth.
- A **divorce/asset split** or **death-of-a-member estate settlement** — heavier to model, but at least one household showing a survivorship transition would meaningfully broaden coverage.

**Recommendation:** Fold at least two discontinuities into existing households (a market dip across all investment snapshots is nearly free and high-value; a bonus/liquidity spike on H3). Reserve the heavier transitions (divorce, death) for a documented future expansion.

### 3.9 Irregular income realism

Related to §3.8 but worth separating: H3 and H5 have business income, but it appears to flow steadily. Genuinely *lumpy* income — 1099/freelance/commission, seasonal swings, K-1 distributions, bonus-heavy comp — is absent. The consulting LLC in H5 and the business income in H3 are the natural places to introduce variance. Smooth income makes budget-vs-actual and cash-flow reporting look easier than reality; spiky income is where those features earn their keep.

### 3.10 Education-funding depth

529 plans exist in H2 and H3 but only as steady accounts. The pillar has more surface worth exercising: **529 superfunding** (the five-year-forward gift-tax election, a common HNW move for grandparents/parents), **UTMA/UGMA custodial accounts**, **private-school tuition** as a recurring expense (realistic for H2/H3), and the **SECURE 2.0 529-to-Roth rollover** (a new, demo-worthy feature). At least the superfunding event and a private-tuition expense line are low-effort, high-realism additions for H2 or H3.

---

## 4. Closing the $13M–$20M gap: a proposed sixth household

The brief targets households "up to $20M," but the current ceiling is $12.86M. The $13M–$20M band is not just "more of the same" — it is precisely where, post-OBBBA, a *single* individual crosses into live **federal** estate-planning territory (the $15M individual exemption), where GST and irrevocable-trust planning become real, and where the concentration/liquidity/charitable pillars converge.

I recommend a **sixth household: a single (widowed) individual, ~$16–18M net worth**, which simultaneously closes several gaps:

- **Single-filer everything** — the entire set is currently couples/families, so single-filer tax brackets, a single Social Security record, and single-member RBAC are all unrepresented. A widowed retiree is a common, clean single-member case.
- **Federal estate exposure at the $15M boundary** — the one place couples can't demonstrate it, since they're sheltered to $30M.
- **Survivorship origin** — wealth that includes a deceased spouse's step-up-in-basis assets and possibly an inherited IRA (§3.5), giving a realistic backstory and exercising the inherited-IRA drawdown.
- **Natural home for the heavier HNW features** — a CRT funded with a low-basis asset (§3.3), an irrevocable trust or ILIT (§3.2), cash-value life for estate liquidity (§3.4), a private-fund commitment with capital calls (§3.7), and an SBLOC (§3.6).

Placing this household in a **state with an estate or inheritance tax below the federal line** (e.g., Oregon at $1M, Massachusetts at $2M, Minnesota at $3M, New York at ~$7.35M with its own "cliff," or Washington) would let it demonstrate *combined* federal + state exposure — complementing H2's pure-state-only exposure in Illinois. New York is attractive because of its well-documented estate "cliff" at ~105% of the exemption. This also rebalances the set, which currently leans heavily toward no-tax states (three of five).

If adding a sixth household is undesirable, the fallback is to **reposition H3 or H5 upward** toward $16–18M and graft the single-filer/estate features onto a restructured H5 — but a clean sixth household is cleaner than overloading H5, which is already carrying the entire decumulation story.

---

## 5. Household-by-household enhancement summary

For ease of handoff, the surgical changes per household:

- **H1 (Chen-Nakamura, Austin, $899K):** add an ESPP (15% discount, lookback); add umbrella liability; add disability insurance; optionally a mega-backdoor Roth if the plan supports it; fold in a short market-dip in investment snapshots.
- **H2 (Okonkwo-Rivera, Naperville IL, $3.4M):** lean into the **Illinois $4M non-portable state estate exposure** with a documented planning note and (if modeled) bypass-trust titling; add umbrella liability; add 529 superfunding and a private-school tuition expense; add LTC insurance consideration; confirm whether the "multi-generation" framing includes actual financial support to an aging parent (gifts/eldercare expenses) and model it if so.
- **H3 (Whitfield-Torres, Brentwood, $9.5M):** the priority retrofit — add **RSU/ISO equity compensation**, a **concentrated single-stock position (~30% of portfolio)**, a **10b5-1 scheduled-sale** diversification pattern, an **AMT event**, a **backdoor Roth**, a **DAF with appreciated-stock contributions**, an **SBLOC**, a **revocable living trust** titling layer, **scheduled/specialty insurance** (e.g., wine/art), and a **bonus/liquidity income spike**. Consider noting the **California Prop 13** assessed-vs-market gap in the property valuation history.
- **H4 (Park-Cole, Nashville, $154.5K):** add an ESPP at one spouse's startup; optionally an **inherited IRA** (SECURE 10-year) as a small, realistic complexity; consider an **MFS-for-IDR** student-loan filing nuance given the student loans already present; fold in a brief unemployment gap for one member.
- **H5 (Langford, Sarasota FL, $12.86M):** add a **Roth-conversion-window** pattern in the 2024 (pre-RMD) history; add a **QCD** satisfying part of the RMD (and note it cannot route to a DAF); add a **cash-value life policy** as an estate-liquidity asset; add **umbrella liability**; add a **T-bill ladder/MMF** for cash management; add **LTC** coverage; add a **revocable living trust** titling layer.
- **H6 (new — proposed):** single/widowed, ~$16–18M, in a state with sub-federal estate/inheritance tax; carries CRT, ILIT/irrevocable trust, inherited IRA, private-fund capital calls, SBLOC, single-filer tax, and single-member RBAC.

---

## 6. Edge cases worth encoding deliberately

These are situations a $20M-capable system should be *seen* to handle, and which make strong demo and test fixtures:

- **State estate tax with no federal exposure (H2/IL):** a household that owes nothing federally but faces a real state liability — the OBBBA-era reality for most affluent families in the 18 estate/inheritance-tax states.
- **The estate-tax "cliff":** Illinois and New York tax from the bottom once the threshold is crossed, not just the excess — a non-obvious computation worth representing.
- **AMT trigger year:** an ISO exercised-and-held that pushes one tax year into AMT, with credit carryforward in later years.
- **Withholding shortfall on a large RSU vest:** the 22% flat supplemental rate under-withholding for a top-bracket earner, producing an April balance due.
- **IRMAA two-year lookback interacting with a one-time income spike:** a Roth conversion or capital-gain event in year *N* raising Medicare premiums in year *N+2* — H5 already has the machinery; a spike would showcase it.
- **Capital-call cash-flow shape:** committed-but-uncalled capital drawn irregularly, distinct from any other transaction pattern.
- **Non-monotonic net worth:** a market drawdown so the headline chart dips and recovers.
- **Survivorship transition:** inherited step-up-in-basis assets and an inherited IRA in the single-filer household.

---

## 7. Intentional omissions (out of scope) — with reasoning

Equally important is being explicit about what should *stay* out, so the dataset's ceiling is a deliberate design choice rather than an apparent gap:

- **Multi-currency / foreign accounts / FX:** the v1 design is USD-only. Foreign-account reporting (FBAR/FATCA) and currency translation are intentionally excluded.
- **Family-office and ultra-HNW structures:** captive insurance, private-placement life insurance (PPLI), family limited partnerships (FLPs), GRATs/SLATs/IDGTs as *active funded* vehicles, and dynasty trusts belong to the >$20M / $50M+ world. The tool's stated ceiling is ~$20M; these should be named as the deliberate upper boundary. (A *revocable* living trust as a titling layer is in scope; *irrevocable* funded vehicles are the boundary line — with an ILIT/CRT on the single-filer household as the one intentional toe over it, justified by the $15M federal boundary.)
- **Gross-salary / payroll-deduction granularity:** explicitly deferred to v2 per the original spec; equity-comp withholding *detail* inherits this deferral, while vest *events* and net *positions* remain in scope.
- **Active tax-return preparation / filing logic:** HearthLedger tracks and reports; it is not a tax-prep engine. AMT, IRMAA, and estate exposures are modeled as *patterns and notes in the data*, not as computed filings.
- **Crypto/digital assets:** in scope mechanically (just another valued asset) but reasonable to mark as a lower-priority optional addition rather than a core requirement.

Documenting these in the spec itself (a short "scope boundary" section) is worth doing, so future contributors don't read the absence of an FLP as an oversight.

---

## 8. Data-model implications (not just seed data)

Several recommendations require schema support, not merely new rows. Flagging them so the spec revision can decide what is v1 vs. deferred:

1. **Ownership/title entity** — to represent revocable trusts (in scope), bypass/credit-shelter trusts, and irrevocable vehicles (boundary). Minimum viable: an account `title`/`ownership_structure` enum plus an optional `trust` record.
2. **Insurance-policy entity** — one structure spanning umbrella, term, permanent (with a cash-value *asset* balance), disability, LTC, and scheduled/specialty, able to post recurring premiums and, where applicable, carry an asset balance.
3. **Equity-compensation grant + vesting schedule** — grant type (RSU/ISO/NSO/ESPP), vesting events, and a link to the resulting holding lot, so vests post as income/asset events.
4. **Cost-basis / lot-level tracking** on investment holdings — prerequisite for concentration reporting and tax-loss harvesting realism.
5. **Capital commitment / called-capital tracking** — a committed amount with a drawn/undrawn balance and call/distribution transactions, for private-fund interests.
6. **SBLOC / margin as a borrowing account** distinct from amortizing loans.

Items 1–4 unlock the four most important missing pillars (estate, insurance, equity comp, concentration) and are worth prioritizing; 5–6 are enrichment for the upper-band households.

---

## 9. References

Estate & gift tax (OBBBA, 2026):
- Pierce Atwood, "The One Big Beautiful Bill Act and Estate Planning" — $15M/$30M permanent exemption, QSBS and §199A changes.
- Morgan Lewis, "Estate Tax Alert: New $15 Million Federal Exemption Becomes Law."
- IRS Revenue Procedure 2025-32 (2026 inflation figures), as reported by Faegre Drinker, "2026 Estate Tax Exemption and Planning Considerations."
- BNY Wealth and ACTEC "Capital Letter" — planning implications of permanence.

State estate tax (Illinois and comparators):
- Illinois Attorney General, Estate Tax Instruction Fact Sheet (Form 700) — $4M threshold, non-portable, cliff structure.
- Faegre Drinker (2026) — state-by-state thresholds (MA $2M, MN $3M, NY $7.35M cliff, etc.).
- Lechner Law Group (June 2026) and Friedman+Huey — Illinois $4M, non-portability, bypass-trust mitigation.
- JRC Insurance Group (2026) — HB2601 $8M proposal status; multi-state list.

Equity compensation & concentration:
- Brady Ware, "Equity Compensation Tax Strategies for High Wealth Individuals" — AMT, 83(b), 10b5-1.
- Carter Financial, "The Executive's Guide to Equity Compensation" — 50–80% net-worth concentration; 10–25% target allocation.
- U.S. Bank, "Equity Compensation: Stock Options and RSUs" — 20% concentration threshold; deferred comp.
- RHA Wealth and True Wealth Design — supplemental-withholding shortfall ("April problem"); multi-year timing.
- True Root Financial — direct indexing / long-short tax-loss harvesting for $3M–$5M+ concentrated positions; SBLOC to fund expenses.

Insurance / risk management:
- Carter Financial; Wheeler & Taylor; MAI Capital — umbrella at ≥ net worth, $5M–$25M typical, low cost.
- EP Wealth, "Do You Have the Right Insurance Coverage for Your Wealth?" — permanent life, ILIT, DI, LTC, premium financing.
- Trusts & Estates (wealthmanagement.com) — life insurance for estate *liquidity* amid illiquid private-market holdings.

Charitable vehicles:
- Fidelity Charitable — DAF mechanics, CRT structures, DAF-as-CRT-remainder; QCD-cannot-fund-DAF rule.
- Slowik Estate Planning — DAF vs CRT; 60%/30% AGI limits; OBBBA 2026 0.5% AGI floor and 35% deduction cap for top earners.
- Pinellas Community Foundation; Greater Houston Community Foundation — CRT in advanced/liquidity-event planning.

*All figures are 2025–2026 and should be re-verified at implementation time; tax thresholds (annual gift exclusion $19,000, QCD limit ~$108,000 for 2025, state exemptions) move with inflation and legislation.*

---

*End of review.*
