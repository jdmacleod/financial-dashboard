# HearthLedger — Demo Dataset Coverage Matrix (Phase F)

Post-revision summary of the six demo households after the demo-data extension
(Phases A–E). Net-worth figures are the `ReportService`-computed values as of
2026-06-21 (end of the seed window), matching each generator's printed summary.

```
H1  Chen-Nakamura    Round Rock TX   Members: 2   NW: ~$1,003,300
H2  Okonkwo-Rivera   Naperville IL   Members: 4   NW: ~$3,620,400
H3  Whitfield-Torres Brentwood CA    Members: 4   NW: ~$10,019,300
H4  Park-Cole        Nashville TN    Members: 2   NW: ~$246,000
H5  Langford         Sarasota FL     Members: 2   NW: ~$13,327,100
H6  Castellano       Scarsdale NY    Members: 1   NW: ~$18,290,000

Six states; NW range ~$246,000 -> ~$18,290,000 (74x spread).
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

| Planning surface / feature | H1 | H2 | H3 | H4 | H5 | H6 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Equity comp — RSU (sell-to-cover) | | | ✓ | | | |
| Equity comp — ISO (held tranche, AMT) | | | ✓ | | | |
| Equity comp — ESPP (discount, lookback) | ✓ | | | ✓ | | |
| Concentrated single-stock position | | | ✓ | | | ✓ |
| Cost-basis lots | ✓ | | ✓ | ✓ | | ✓ |
| Revocable living trust (titling) | | ✓ | ✓ | | ✓ | ✓ |
| Bypass / credit-shelter trust (documented, unfunded) | | ✓ | | | | |
| ILIT (irrevocable life insurance trust) | | | | | | ✓ |
| CRT (charitable remainder unitrust) | | | | | | ✓ |
| Donor-advised fund (held away) | | | ✓ | | | ✓ |
| QCD (RMD-satisfying, income-excluded) | | | | | ✓ | ✓ |
| Backdoor Roth | | ✓ | ✓ | | ✓ | |
| Roth-conversion window (pre-RMD) | | | | | ✓ | |
| Inherited IRA (SECURE 10-year) | | | | | | ✓ |
| Capital commitment (PE, capital calls) | | | | | | ✓ |
| SBLOC (revolving credit line) | | | ✓ | | | ✓ |
| Umbrella liability | ✓ | ✓ | | | ✓ | ✓ |
| Permanent / cash-value life (asset) | | | | | ✓ | ✓ |
| ILIT-owned permanent life (excluded from NW) | | | | | | ✓ |
| Disability insurance | ✓ | | | | | |
| Long-term-care insurance | | ✓ | | | ✓ | ✓ |
| Scheduled / specialty insurance | | | ✓ | | | ✓ |
| Collectible asset (manually valued) | | | ✓ wine | | | ✓ art |
| 529 superfunding (5-year election) | | ✓ | | | | |
| Private-school tuition | | ✓ | | | | |
| State estate tax exposure | | ✓ IL | | | | ✓ NY |
| Single-member RBAC (one principal, no grants) | | | | | | ✓ |
| Single-filer tax / single-filer IRMAA | | | | | | ✓ |
| Market-dip discontinuity (non-monotonic NW) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Unemployment gap (income stop + spend-down) | | | | ✓ | | |
| Bonus / liquidity income spike | | | ✓ | | | |

**NSO** is the one equity-compensation grant type with a category
(`nso_exercise_income`) but no household exercising it; RSU, ISO, and ESPP cover
the equity-comp surface. It is available for a future household without further
schema or taxonomy work.

---

## Final acceptance criteria (Phase F)

1. **`--household 6` and `--household all` run clean and idempotently** under
   deterministic seeding. ✓ Verified: all six seed; a second `--household all`
   skips all six.
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
