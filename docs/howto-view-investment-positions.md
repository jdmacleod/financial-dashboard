# How to view your investment positions and holdings mix

See your brokerage holdings rolled up by security ("Top positions") and by asset
class ("Holdings mix") on the Investments page.

## Prerequisites

- HearthLedger running at `http://localhost`
- Logged in as any member who can see at least one `investment_brokerage` account
- At least one **cost-basis lot** recorded against a brokerage account (see
  [Where positions come from](#where-positions-come-from) below — the demo data
  already includes lots)

## What you'll see

Open **Reports → Investments** (`/reports/investments`). Below the account cards,
a **Holdings** card appears with two halves:

- **Top positions** — a table with one row per ticker, showing **Ticker**,
  **Shares**, and **Cost basis**. Lots for the same ticker across different
  accounts are summed into a single row, ranked by cost basis (largest first),
  capped at the top 10.
- **Holdings mix** — a donut plus legend that groups your cost basis by asset
  class (Equity, Fixed income, Cash, Real estate, Alternatives, Other, or
  Unclassified), with each slice's share of the total.

> The figures are **cost basis**, not market value. HearthLedger does not track
> live prices, so there is no "current value" or gain/loss on this card. The note
> "Cost basis shown — HearthLedger does not track live market prices" appears
> under the table.

The whole Holdings card stays hidden until at least one lot exists.

## Where positions come from

Positions are rolled up from **cost-basis lots** — individual purchase records
(ticker, shares, basis per share, acquired date). Lots are created two ways:

1. **Demo data.** The Chen-Nakamura, Whitfield-Torres, Park-Cole, and Castellano
   households seed brokerage lots, so positions show up immediately after you seed
   demo data. Common tickers (VTI, BND, NVDA, and so on) are auto-classified, so
   the Holdings mix is meaningful out of the box.
2. **The API.** Add a lot with a `POST` to `/investment-lots`. There is no
   add-a-lot form in the UI yet — the existing **Cost-basis lots** card on the
   Investments page is read-only.

To add a lot with an asset class so it lands in the right Holdings-mix slice:

```bash
curl -X POST http://localhost/api/v1/investment-lots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "<brokerage account uuid>",
    "ticker": "VTI",
    "shares": "30",
    "basis_per_share": "200.00",
    "acquired_date": "2022-01-01",
    "basis_type": "purchase",
    "asset_class": "equity"
  }'
```

`asset_class` is optional and accepts `equity`, `fixed_income`, `cash`,
`real_estate`, `alternative`, or `other`. Leave it off and the lot lands in the
**Unclassified** slice.

## Verification

Fetch the rollup directly and confirm it matches the page:

```bash
curl -s http://localhost/api/v1/investment-positions \
  -H "Authorization: Bearer $TOKEN" | jq
```

You should see a `positions` array (one entry per ticker, sorted by
`cost_basis`), a `holdings_mix` array (one entry per asset class with a
`percentage`), and a `total_cost_basis`. The `total_cost_basis` equals the sum of
`shares × basis_per_share` across every visible lot.

## Troubleshooting

- **The Holdings card never appears.** You have no lots. Seed demo data, or add a
  lot via the API. An `investment_brokerage` account with only a balance (no lots)
  shows an account card but no Holdings rollup.
- **Everything is in the "Unclassified" slice.** Your lots have no `asset_class`.
  Set it on each lot via `PATCH /investment-lots/{lot_id}`, or rely on the demo
  seed's ticker auto-classification.
- **A holding is missing.** Positions only include accounts you can see. If a
  brokerage account is restricted by visibility rules, its lots are excluded from
  your rollup.

## Related

- Reference: `GET /investment-positions` and `GET /investment-lots` in [`api-reference.md`](./api-reference.md)
- Reference: the `investment_lot` table in [`data-model.md`](./data-model.md)
- Tutorial: [Explore portfolio and retirement insights](./tutorial-portfolio-and-retirement-insights.md)
