# How to read the retirement income breakdown

See how much of your income comes from Social Security, a pension, and required
minimum distributions (RMDs), broken out as labeled buckets on the Cash Flow
report.

## Prerequisites

- HearthLedger running at `http://localhost`
- Logged in as any member
- Income transactions categorized as **Social Security**, **Pension Income**, or
  **Required Minimum Distribution** in the date range you're viewing (the
  Langford demo household has all three)

## Steps

1. Open **Reports → Cash Flow** (`/reports/cash-flow`).

2. Set the **Date range** to a period that includes retirement income. For the
   Langford demo household, any 2025 range works (Bob draws Social Security, a
   pension, and quarterly RMDs).

3. Look below the income/expense chart for the **Retirement income** card. It
   shows four figures:

   | Bucket              | What it sums                                           |
   | ------------------- | ------------------------------------------------------ |
   | **Social Security** | Income in the "Social Security" category               |
   | **Pension**         | Income in the "Pension Income" category                |
   | **RMDs**            | Income in the "Required Minimum Distribution" category |
   | **Total**           | The three buckets added together                       |

The buckets are a subset of the **Total income** KPI at the top; they break out
the retirement slice of your income, they do not add to it.

## How the buckets are filled

The breakdown matches transactions by **category name**. Any income transaction
in a category named exactly `Social Security`, `Pension Income`, or
`Required Minimum Distribution` is counted. These categories are part of the
standard demo taxonomy; if you create your own, name them the same way to feed the
breakdown.

The card **hides itself** when all three buckets are zero, so households that
aren't drawing retirement income never see an empty panel.

## Verification

Fetch the report and confirm the `retirement_income` block:

```bash
curl -s "http://localhost/api/v1/reports/cash-flow?from=2025-01-01&to=2025-12-31" \
  -H "Authorization: Bearer $TOKEN" | jq '.retirement_income'
```

You should see `social_security`, `pension`, `rmd`, `total`, and `has_data`.
`has_data` is `true` only when `total` is greater than zero, the same flag the
page uses to decide whether to render the card.

## Troubleshooting

- **The card doesn't appear.** No income in the three categories for that range,
  so `has_data` is `false`. Widen the date range or check that your retirement
  income is categorized correctly.
- **A category isn't counted.** The match is on the exact category name. A
  category called "SS" or "Pension" (instead of "Social Security" / "Pension
  Income") won't be bucketed. Rename it to match.
- **A retirement deposit shows in Total income but not a bucket.** It is
  categorized as ordinary income, not one of the three retirement categories.
  Recategorize the transaction.

## Related

- User guide: [Cash Flow report](./user-guide.md#cash-flow)
- Reference: `GET /reports/cash-flow` (`retirement_income`) in [`api-reference.md`](./api-reference.md)
- Tutorial: [Explore portfolio and retirement insights](./tutorial-portfolio-and-retirement-insights.md)
