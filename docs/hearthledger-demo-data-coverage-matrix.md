# HearthLedger — Demo Dataset Coverage Matrix (Phase F)

Post-revision summary of the seven demo households after the demo-data extension
(Phases A–E) plus the H7 early-accumulation opener. Net-worth figures are the
`ReportService`-computed values as of 2026-06-21 (end of the seed window), matching
each generator's printed summary.

```
H7  Brooks           Atlanta GA      Members: 1   NW: ~$12,200
H4  Park-Cole        Nashville TN    Members: 2   NW: ~$279,500
H1  Chen-Nakamura    Round Rock TX   Members: 2   NW: ~$1,003,300
H2  Okonkwo-Rivera   Naperville IL   Members: 4   NW: ~$3,620,400
H3  Whitfield-Torres Brentwood CA    Members: 4   NW: ~$9,902,500
H5  Langford         Sarasota FL     Members: 2   NW: ~$13,327,100
H6  Castellano       Scarsdale NY    Members: 1   NW: ~$18,290,000

Seven states; NW range ~$12,200 -> ~$18,290,000 (1,500x spread).
Estate exposure represented:
  - state-only ...................... Illinois cliff (H2)
  - none (federal, married couple) .. H3, H5 (sheltered under the $30M couple exemption)
  - federal + state cliff, single ... New York (H6), ~$3.3M over the $15M single exemption
```

> Note on net-worth figures: these differ from the spec's original `~` targets.
> Most of the drift is a pre-existing data-quality gap — the prior summary
> literals were hand-estimates that undercounted the grown snapshot series and
> never matched the app's own net-worth report. Phase C reconciled every
> household's printed net worth to the actual `ReportService` computation, plus
> the new in-net-worth accounts in H3/H5/H6. H6 is built to its inventory and
> lands at exactly $18,290,000.

---

## Cross-household feature matrix

✓ = represented in that household.

| Planning surface / feature                           | H1  |  H2  |   H3   | H4  | H5  |  H6   | H7  |
| ---------------------------------------------------- | :-: | :--: | :----: | :-: | :-: | :---: | :-: |
| Equity comp — RSU (sell-to-cover)                    |     |      |   ✓    |     |     |       |     |
| Equity comp — ISO (held tranche, AMT)                |     |      |   ✓    |     |     |       |     |
| Equity comp — ESPP (discount, lookback)              |  ✓  |      |        |  ✓  |     |       |     |
| Equity comp — NSO (exercise & hold, private co.)     |     |      |        |  ✓  |     |       |     |
| Concentrated single-stock position                   |     |      |   ✓    |     |     |   ✓   |     |
| Cost-basis lots                                      |  ✓  |      |   ✓    |  ✓  |     |   ✓   |     |
| Revocable living trust (titling)                     |     |  ✓   |   ✓    |     |  ✓  |   ✓   |     |
| Bypass / credit-shelter trust (documented, unfunded) |     |  ✓   |        |     |     |       |     |
| ILIT (irrevocable life insurance trust)              |     |      |        |     |     |   ✓   |     |
| CRT (charitable remainder unitrust)                  |     |      |        |     |     |   ✓   |     |
| Donor-advised fund (held away)                       |     |      |   ✓    |     |     |   ✓   |     |
| QCD (RMD-satisfying, income-excluded)                |     |      |        |     |  ✓  |   ✓   |     |
| Backdoor Roth                                        |     |  ✓   |   ✓    |     |  ✓  |       |     |
| Mega-backdoor Roth (after-tax 401k, in-plan conv.)   |  ✓  |      |        |     |     |       |     |
| Roth-conversion window (pre-RMD)                     |     |      |        |     |  ✓  |       |     |
| Inherited IRA (SECURE 10-year)                       |     |      |        |  ✓  |     |   ✓   |     |
| Capital commitment (PE, capital calls)               |     |      |        |     |     |   ✓   |     |
| SBLOC (revolving credit line)                        |     |      |   ✓    |     |     |   ✓   |     |
| Margin loan (brokerage, maintenance call)            |     |      |   ✓    |     |     |       |     |
| Umbrella liability                                   |  ✓  |  ✓   |        |     |  ✓  |   ✓   |     |
| Permanent / cash-value life (asset)                  |     |      |        |     |  ✓  |   ✓   |     |
| ILIT-owned permanent life (excluded from NW)         |     |      |        |     |     |   ✓   |     |
| Disability insurance                                 |  ✓  |      |        |     |     |       |     |
| Long-term-care insurance                             |     |  ✓   |        |     |  ✓  |   ✓   |     |
| Scheduled / specialty insurance                      |     |      |   ✓    |     |     |   ✓   |     |
| Collectible asset (manually valued)                  |     |      | ✓ wine |     |     | ✓ art |     |
| 529 superfunding (5-year election)                   |     |  ✓   |        |     |     |       |     |
| Private-school tuition                               |     |  ✓   |        |     |     |       |     |
| State estate tax exposure                            |     | ✓ IL |        |     |     | ✓ NY  |     |
| Single-member RBAC (one principal, no grants)        |     |      |        |     |     |   ✓   |  ✓  |
| Single-filer tax / single-filer IRMAA                |     |      |        |     |     |   ✓   |     |
| Market-dip discontinuity (non-monotonic NW)          |  ✓  |  ✓   |   ✓    |  ✓  |  ✓  |   ✓   |  ✓  |
| Unemployment gap (income stop + spend-down)          |     |      |        |  ✓  |     |       |     |
| Eldercare / sandwich-generation cash flow            |     |  ✓   |        |     |     |       |     |
| Bonus / liquidity income spike                       |     |      |   ✓    |     |     |       |     |
| Early accumulation — low net worth, debt-as-hero     |     |      |        |     |     |       |  ✓  |
| Multi-debt avalanche != snowball (extra payment)     |     |      |        |     |     |       |  ✓  |
| HSA invested (triple-tax)                            |     |      |        |  ✓  |     |       |  ✓  |

All four equity-compensation grant types (RSU, ISO, ESPP, NSO) are now exercised
by a household: RSU/ISO at H3, ESPP at H1/H4, and NSO at H4 (a private-company
exercise-and-hold tranche). Both revolving credit-line types are represented —
SBLOC at H3/H6 and a brokerage margin loan at H3.

H7 Brooks is deliberately the low-complexity entry household: it carries none of
the affluent surfaces above. Its job is the lifecycle opening chapter and the
validation paths the other six can't reach (low net worth, debt elimination as the
hero, and a multi-debt avalanche-vs-snowball comparison that actually diverges with
an extra payment — verified to save ~$367 at $500/mo extra).

---

## Life-stage casting matrix

The lineup is cast across life stages, not just net-worth tiers. Net worth is driven
by two different forces: **LIFECYCLE** households (H7, H4, H1) are pinned to roughly
the top 10–15% for their age; **FEATURE** households (H2, H3, H5, H6) are pinned to
the minimum wealth that credibly trips their target feature (an IL estate cliff needs
~$4M, a NY single estate cliff needs >$15M, PE/ILIT/CRT need UHNW), which is well
above the top-15% band. Estate/PE/trust features can't be demonstrated on a top-15%
household, so the upper tiers are intentionally wealthier — not "unrealistically rich."

| H   | Household        | Age(s) | NW      | %-for-age           | Life stage             | Driver                 |
| --- | ---------------- | ------ | ------- | ------------------- | ---------------------- | ---------------------- |
| H7  | Brooks           | 27     | ~$12.2k | top ~10-15% income  | Early accumulation     | LIFECYCLE              |
| H4  | Park-Cole        | 28/29  | $279.5k | top ~10% NW-for-age | Early-career affluent  | LIFECYCLE              |
| H1  | Chen-Nakamura    | 42/44  | $1.0M   | top ~10-15%         | Mid-career peak-saving | LIFECYCLE              |
| H2  | Okonkwo-Rivera   | 45/47  | $3.6M   | top ~5%             | Established family     | FEATURE (IL estate)    |
| H3  | Whitfield-Torres | 51/54  | $9.9M   | top ~1-2%           | Peak-earning exec      | FEATURE (equity/SBLOC) |
| H5  | Langford         | 64/74  | $13.3M  | top ~1%             | Recently retired       | FEATURE (Roth window)  |
| H6  | Castellano       | 74     | $18.3M  | top <1%             | Widowed, legacy/estate | FEATURE (NY estate)    |

Axis note: H1–H6's "%-for-age" is a **net-worth** percentile. H7's is an **income**-
for-age percentile (top ~10-15%); its net-worth percentile for age is deliberately
low — that is the point of the rung. **H4 is early-career _affluent_** ($279.5k reads
65th-percentile against _all_ US households but is ~top-decile for under-30); it is not
a "modest" household. H7 is the rung below it: building from a low base.

Negative-net-worth rendering was validated (2026-06-25): H7 was temporarily driven to
~-$48k (a +$60k liability on the student loan) and the Net Worth report and Dashboard
both render correctly — the chart Y-axis auto-scales below zero with a $0 gridline, the
net-worth line sits in the negative region, KPI cards / period table / breakdown bars
format negatives, the change-% math uses `Math.abs`, and no NaN/console errors appear.
FIRE is unaffected (it draws on the investable portfolio, not net worth). The app
needed no code change. H7 ships positive (~$12.2k); to re-check, add a large liability
to drive net worth negative.

---

## Final acceptance criteria (Phase F)

1. **`--household 7` and `--household all` run clean and idempotently** under
   deterministic seeding. ✓ Verified: all seven seed; a second `--household all`
   skips all seven.
2. **Each household's computed net worth matches its sanity-check target.** ✓
   Every generator's printed `net_worth` equals `ReportService.current_net_worth`
   as of 2026-06-21. H6 = $18,290,000, matching the spec inventory.
3. **H6 produces exactly one principal and zero `account_access_grants`.** ✓
   Verified (members=1, grants=0).
4. **ILIT/CRT/DAF assets excluded from H6 net worth and taxable-estate figures;
   the revocable trust's assets are included.** ✓ The CRT account ($2.5M), the
   ILIT-owned policy, and the DAF ($1.1M) are excluded via
   `counts_in_personal_net_worth=false` / `include_in_net_worth=false`;
   revocable-trust-titled accounts remain in net worth.
5. **Every advisory note specified in Phases C–E exists and is anchored
   correctly.** ✓ 22 advisory notes across H1–H6 (estate 2, tax 3,
   concentration 3, insurance 5, retirement 3, charitable 4, scope_omission 2),
   including the `scope_omission` notes on H3 and H6.
6. **`docs/scope-boundaries.md` exists and enumerates the intentional
   omissions.** ✓ Written to the reference spec at
   `~/Documents/hearthledger-spec/docs/scope-boundaries.md` (five omissions with
   reasoning).
7. **Service-layer postings (Phase A):** a vesting event atomically creates a
   lot + income transaction + sell-to-cover transfer via an `@audit` method; a
   capital call increases `called_to_date` and posts a `capital_call` transfer;
   an SBLOC draw posts a `sbloc_draw` transfer with monthly `sbloc_interest`. ✓
   Covered by `tests/unit/test_demo_extension_services.py`.
8. **No new encrypted field appears in any audit-log payload.** ✓
   `ownership_entity.name_enc` and `capital_commitment.fund_name_enc` are in the
   audit exclusion set; covered by tests.
