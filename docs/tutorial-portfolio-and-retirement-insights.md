# Tutorial: explore portfolio and retirement insights

By the end of this tutorial you'll have used three v0.15.0.0 features on real
demo data: the **investment positions** rollup, the **retirement income**
breakdown, and a pension's **present value** on your net worth. You'll switch
between two demo households: a working family with a brokerage portfolio, and a
retired couple drawing Social Security, a pension, and RMDs.

You'll see the first result within three steps.

## What you'll need

- HearthLedger running at `http://localhost` (see
  [getting-started.md](./getting-started.md) if it isn't up yet)
- A terminal for the one seed command
- About 10 minutes

Every demo account uses the password **`HearthDemo1!`**.

## Step 1: Seed the demo households

Load the five sample households:

```bash
docker-compose exec backend python scripts/seed_demo_data.py --household all
```

This creates the Chen-Nakamura family (a brokerage portfolio) and the Langford
couple (retired), among others. Full details are in
[demo-quickstart.md](./demo-quickstart.md).

## Step 2: Log in as the Chen-Nakamura household

Open `http://localhost` and sign in:

- **Email:** `wei@chen-nakamura.local`
- **Password:** `HearthDemo1!`

## Step 3: See your investment positions

Go to **Reports → Investments** (`/reports/investments`). Scroll past the account
cards to the **Holdings** card. You're now looking at your first result:

- **Top positions**: each ticker the household holds, with total shares and cost
  basis, biggest holding first.
- **Holdings mix**: a donut splitting that cost basis across asset classes
  (Equity, Fixed income, and so on). The demo classifies common tickers
  automatically, so the mix is populated, not all "Unclassified."

Notice there's no "current value" column. HearthLedger tracks **cost basis**, not
live prices; the note under the table says so. That's a deliberate scope choice:
a balance tracker, not a brokerage terminal.

> Want to add your own holding? Positions roll up from cost-basis lots, which you
> add via `POST /investment-lots`. See
> [How to view your investment positions](./howto-view-investment-positions.md).

## Step 4: Switch to the retired Langford household

Sign out, then sign back in as the Langford primary:

- **Email:** `bob@langford.local`
- **Password:** `HearthDemo1!`

Bob is retired and draws three kinds of retirement income, exactly what the next
feature breaks out.

## Step 5: Read the retirement income breakdown

Go to **Reports → Cash Flow** (`/reports/cash-flow`) and set the date range to
all of 2025. Below the income/expense chart, the **Retirement income** card shows
four figures:

- **Social Security**, **Pension**, and **RMDs**: each summing Bob's income in
  that category
- **Total**: the three combined

These break out the retirement slice of the **Total income** KPI at the top; they
don't add to it. If you pointed the date range at a working household instead, the
card would simply not appear; it hides itself when there's no retirement income.

## Step 6: Give the pension a present value

The Langford household draws a pension _as income_, but the demo doesn't include a
pension **record**, so net worth shows no pension value yet. Add one:

1. On the **Accounts** page, add an account of type `pension` (e.g. "Bob's
   Pension") via the Retirement group.
2. Open it, click **Add pension details**, and enter a **Monthly benefit
   estimate** of `4000` and a **COLA** of `0.02`. Mark it **Vested**. Bob is
   already retired, so leave the eligibility date in the past (or blank), so the
   benefit is in payment, not deferred. Save.
3. Go to **Reports → Net Worth** (`/reports/net-worth`). Below the chart, the
   pension is listed. Click **Show PV**.

The figure flips from `$48,000 / yr` to a present value, the economic worth of
that benefit today, valued as a finite life annuity with COLA growth. (Because
Bob is already eligible, there's no deferral discount; for a worker years from
retirement, the PV would be discounted back to today.) That single number lets the
pension sit next to the brokerage and property balances on your net worth.

Now edit the estimate to `4500` and save. The PV rises from today forward, but the
**historical** points on the net-worth chart keep their original valuation.
HearthLedger records a dated snapshot of each estimate and values every past month
from the estimate that was in effect then.

## What you built

You used all three v0.15.0.0 features end to end:

- **Investment positions**: a per-ticker rollup and asset-class mix from
  cost-basis lots (Chen-Nakamura).
- **Retirement income**: Social Security, pension, and RMD income broken out on
  the Cash Flow report (Langford).
- **Pension present value**: a defined-benefit pension valued onto your net
  worth, with edits that don't rewrite history (Langford).

Where to go next:

- [How to view your investment positions](./howto-view-investment-positions.md)
- [How to read the retirement income breakdown](./howto-track-retirement-income.md)
- [How to give a pension a present value](./howto-set-pension-present-value.md)
- [Why pension present value works the way it does](./explanation-pension-present-value.md)
