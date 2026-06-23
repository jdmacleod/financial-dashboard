# Why pension present value works the way it does

A defined-benefit pension pays a monthly amount for life once you retire. That
is real wealth, but it does not show up as an account balance you can chart next
to a brokerage account. HearthLedger turns the promised benefit into a single
**present value (PV)** number so a pension can sit alongside the rest of your net
worth. This doc explains how that number is computed, why the model changed in
v0.15.0.0, and how editing an estimate avoids rewriting your history.

The math lives in `backend/app/services/pension_valuation.py`. The values it
produces appear on the **Net Worth** report (the **Show PV** toggle) and in the
`estimated_pv` field of the net-worth API response.

## The problem

A pension's value is "$4,000 a month, starting at 65, for the rest of your
life." To compare that to a $500,000 brokerage balance you need one number in
today's dollars. Two things make that hard:

1. **Timing.** A 40-year-old whose pension starts at 65 should not count it the
   same as a 66-year-old already drawing it. The 40-year-old waits 25 years
   before the first check.
2. **The benefit is not flat.** Most pensions have a cost-of-living adjustment
   (COLA), and many continue paying a reduced amount to a surviving spouse.

The first version of HearthLedger valued a pension as a simple **perpetuity**:

```
PV = annual_benefit / 0.04
```

That is `$48,000 / 0.04 = $1,200,000` for a $4,000/month benefit. It is easy to
reason about, but it is wrong in two directions: it assumes the benefit is paid
**forever** (a perpetuity never ends, a life annuity does), and it ignores the
**years until eligibility** entirely. For a young worker far from retirement, the
perpetuity badly overstates the value.

## The approach

v0.15.0.0 replaces the perpetuity with a **finite, growing life annuity that is
discounted back from the date benefits begin.** Four inputs drive it, all stored
on the pension record:

| Input                      | Role                                                |
| -------------------------- | --------------------------------------------------- |
| `monthly_benefit_estimate` | The benefit; `× 12` gives the first-year annual pay |
| `cola_adjustment_rate`     | Annual growth of each payment (the COLA)            |
| `eligibility_date`         | When payments start (drives the deferral discount)  |
| `survivor_benefit_percent` | Fraction a survivor keeps after the primary horizon |

The discount rate is fixed at **4%** (`PENSION_DISCOUNT_RATE`). Two horizon
constants shape the annuity: the benefit is valued over a **25-year** payout
(`DEFAULT_PAYOUT_YEARS`, a life-annuity stand-in), and a survivor draws the
reduced benefit for an additional **10 years** (`SURVIVOR_PAYOUT_YEARS`).

The calculation runs in three moves:

```
1. Growing annuity at the start of payments
   ┌─────────────────────────────────────────────┐
   │ value of a benefit that pays annual in year 1,│
   │ grows at the COLA each year, discounted at 4%,│
   │ for 25 years                                  │
   └─────────────────────────────────────────────┘
                      │
2. Add the survivor tail (if survivor_benefit_percent is set)
   the reduced benefit for 10 more years, discounted back
   over the 25-year primary horizon
                      │
3. Discount the whole stream back to today
   if eligibility_date is in the future, divide by
   (1.04) ^ (years until eligibility)
```

A benefit already in payment (no future eligibility date) skips step 3, since
there is nothing to wait for. A benefit that starts in 25 years gets divided by
`1.04^25 ≈ 2.67`, so it is worth far less today than the same benefit in payment.
That is the behavior the perpetuity could not express.

For the same $4,000/month benefit already in payment with a 2% COLA, the finite
model lands well under the old `$1,200,000`: a finite life annuity is worth
strictly less than an infinite one. You can see this trade-off directly in the
unit tests (`backend/tests/unit/test_pension_valuation.py`):
`test_finite_annuity_is_less_than_perpetuity` and
`test_deferred_benefit_worth_less_than_in_pay`.

## Why editing an estimate must not rewrite history

The net-worth chart plots one point per month. A pension contributes its PV to
every point. If the PV were always computed from **today's** estimate, then the
day you bump your benefit estimate from $2,000 to $2,500, **every historical
point on the chart would jump**, as if you had always had the higher benefit.
That is misleading: last March your best estimate really was $2,000.

`PensionEstimateHistory` (migration 0010) fixes this. Each row is a snapshot of
the PV inputs with an `effective_date`:

```
effective_date   monthly_benefit_estimate   ...
2024-01-01       2000.00                     ← original estimate
2026-06-23       2500.00                     ← the day you bumped it
```

When the report values a pension at a given date, it picks the snapshot **in
effect at that date**: the latest row whose `effective_date` is on or before the
point (`effective_estimate` in `pension_valuation.py`). So:

- March 2025 is valued from the $2,000 snapshot.
- July 2026 is valued from the $2,500 snapshot.
- A date before the earliest snapshot uses the earliest one (the original
  estimate applies to all prior history).

`PensionService` writes a snapshot on create and again whenever a PV-relevant
field changes (same-day edits update the existing row rather than stacking). The
column names mirror `pension_accounts` on purpose, so the same valuation function
values either a live pension or a historical snapshot, with no duplicate math.

## Trade-offs

- **The 4% rate and 25/10-year horizons are fixed constants, not user inputs.**
  This keeps every pension valued the same way across the whole app, at the cost
  of personalization. Someone who wants a 3% discount rate cannot set one.
- **The 25-year horizon is a stand-in for life expectancy, not an actuarial
  table.** It does not use the member's age or a mortality curve. A precise model
  would, but that is a larger build for a household tracker.
- **The value is still an estimate.** It is meant to give a sense of scale next
  to your portfolio, not to price an annuity for sale. The Net Worth report says
  as much under the **Show PV** toggle.
- **Pensions created before the history table** (or imported without going through
  the service) fall back to their current fields when no snapshots exist. The
  v0.15.0.0 migration backfills one snapshot per existing pension so this is rare.

## Related

- How-to: [Set a pension's present value](./howto-set-pension-present-value.md)
- Reference: pension PV inputs and `estimated_pv` in [`api-reference.md`](./api-reference.md) (`GET /reports/net-worth`)
- Reference: the `pension_estimate_history` table in [`data-model.md`](./data-model.md)
- Tutorial: [Explore portfolio and retirement insights](./tutorial-portfolio-and-retirement-insights.md)
