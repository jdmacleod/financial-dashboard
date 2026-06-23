# How to give a pension a present value on your net worth

Record a defined-benefit pension's benefit estimate so HearthLedger can show its
present value (PV) alongside the rest of your net worth, and understand why later
edits don't rewrite your history.

## Prerequisites

- HearthLedger running at `http://localhost`
- Logged in as a **Primary** or **Partner** member (write access)

> The demo households seed pension **income transactions** but not pension
> **records**, so the demo's net worth shows no pension PV until you add a pension
> record yourself. This guide walks through that.

## Steps

1. **Add a pension account.** On the **Accounts** page, use the Retirement group's
   **+** to reach the Retirement report, then add an account of type `pension`
   (e.g. "State Teachers Pension").

2. **Open the pension account** and find the **Pension details** card. Click
   **Add pension details** (or the pencil icon) to open the editor.

3. **Enter the benefit.** At minimum, set:

   | Field                        | Example       | Why it matters                         |
   | ---------------------------- | ------------- | -------------------------------------- |
   | **Monthly benefit estimate** | `4000`        | The benefit; nothing values without it |
   | **Eligibility age or date**  | `65` / a date | A future date defers (lowers) the PV   |
   | **COLA adjustment rate**     | `0.02` (2%)   | Grows each future payment              |
   | **Survivor benefit %**       | `0.5` (50%)   | Adds a survivor tail to the value      |

   Save. You'll see a "saved" confirmation.

4. **View the present value.** Open **Reports → Net Worth**
   (`/reports/net-worth`). Below the chart, the pension is listed with its annual
   benefit. Click **Show PV** to switch the figure from `$48,000 / yr` to its
   present value, e.g. `$690,000 PV`. A note beneath the list explains the model:
   the present value uses a 4% discount rate, COLA growth, and the time until
   eligibility, valuing the benefit as a finite life annuity rather than a
   perpetuity.

The PV is also added into the pension's contribution to **total net worth**, so
the headline number reflects it whether or not the toggle is on.

## How edits are recorded over time

Every time you save a change to the benefit estimate (or COLA, survivor percent,
or eligibility date), HearthLedger records a dated **estimate snapshot**. When the
net-worth chart values the pension at a past month, it uses the snapshot that was
in effect **then**, not today's number. So bumping your estimate from $2,000 to
$2,500 today raises the value from today forward and **leaves last year's chart
points untouched**.

You don't manage these snapshots; they're written automatically on create and on
each PV-relevant edit. See
[Why pension present value works the way it does](./explanation-pension-present-value.md)
for the model and the history design.

## Verification

After saving, confirm the value flows into the report:

```bash
curl -s "http://localhost/api/v1/reports/net-worth?from=2025-01-01&to=2025-12-31" \
  -H "Authorization: Bearer $TOKEN" | jq '.pension_annotations'
```

Each pension with an estimate has an `estimated_pv` field, the same number the
**Show PV** toggle displays. It is `null` when no benefit estimate is recorded.

## Troubleshooting

- **No "Show PV" toggle appears.** The pension has no monthly benefit estimate.
  Open the pension details editor and set one.
- **The PV looks low for a young worker.** That's expected. A benefit that starts
  in 20+ years is discounted heavily back to today, and that deferral is the point.
- **An old chart point changed after I edited the estimate.** It shouldn't, for
  dates after the original estimate was recorded. If you edited a pension created
  before v0.15.0.0 that had no snapshots, the first edit establishes the baseline;
  subsequent edits are history-aware.

## Related

- Explanation: [Why pension present value works the way it does](./explanation-pension-present-value.md)
- User guide: [Pension accounts](./user-guide.md#pension-accounts) and [Net Worth report](./user-guide.md#net-worth)
- Reference: `GET /reports/net-worth` and the pension endpoints in [`api-reference.md`](./api-reference.md)
