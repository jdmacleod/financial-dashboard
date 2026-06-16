# Phase 3 — Analysis and Reporting

Implements all core analysis views: net worth over time, cash flow,
spending by category, budget vs actuals, property P&L, and the
audit log UI pages.

---

## Deliverables

- [ ] Net worth over time (monthly time series)
- [ ] Cash flow: income vs expenses by month
- [ ] Spending by category (with drilldown)
- [ ] Budget CRUD and vs-actuals comparison
- [ ] Property P&L report (Amendment 3)
- [ ] Dashboard summary page with key metric cards
- [ ] Settings > Activity log page (primary only)
- [ ] Settings > Security log page (own events; primary sees all)
- [ ] Per-record history panel on transactions and accounts

---

## Report endpoints

All report endpoints are read-only and respect `VisibilityContext` —
they only include data from accounts visible to the requesting user.

### Net worth

```
GET /api/v1/reports/net-worth
  query: from (date), to (date), interval (monthly | quarterly | annual)

response:
{
  "series": [
    {
      "date": "2024-01-31",
      "total_assets": 485000.00,
      "total_liabilities": 312000.00,
      "net_worth": 173000.00,
      "breakdown": {
        "checking_savings": 24500.00,
        "investment": 148000.00,
        "retirement": 201000.00,
        "real_estate": 420000.00,
        "hsa": 8200.00,
        "other_assets": 0.00,
        "mortgage": -298000.00,
        "other_liabilities": -14000.00
      }
    },
    ...
  ],
  "current": { ... }  // most recent data point
}
```

**Net worth calculation logic:**

Assets: sum of most recent `account_snapshots.balance` for each account
where `include_in_net_worth = TRUE` and account_type is an asset type.
For checking/savings/credit cards without snapshots, use the sum of
all transactions (running balance).

Liabilities: sum of most recent `debts.current_balance` for loan/mortgage
accounts, or most recent snapshot balance for credit cards.

Net worth at a given month-end date: use the most recent snapshot
on or before that date for each account.

### Cash flow

```
GET /api/v1/reports/cash-flow
  query: from, to, group_by (month | quarter)

response:
{
  "series": [
    {
      "period": "2024-01",
      "income": 11250.00,
      "expenses": 7840.00,
      "net": 3410.00,
      "savings_rate": 0.303
    },
    ...
  ],
  "totals": { "income": ..., "expenses": ..., "net": ..., "savings_rate": ... }
}
```

Income = sum of transactions where `category.is_income = TRUE` and
`is_transfer = FALSE`.
Expenses = sum of ABS(transactions) where `category.is_income = FALSE` and
`is_transfer = FALSE` and amount < 0.

### Spending by category

```
GET /api/v1/reports/spending-by-category
  query: from, to, parent_category_id? (drilldown)

response:
{
  "total": 7840.00,
  "categories": [
    {
      "category_id": "uuid",
      "name": "Housing",
      "amount": 2800.00,
      "percentage": 35.7,
      "transaction_count": 3,
      "has_children": true
    },
    ...
  ]
}
```

When `parent_category_id` is supplied, returns subcategory breakdown.
Transactions with no category are grouped under "Uncategorized".

### Budget vs actuals

```
GET /api/v1/reports/budget-vs-actuals
  query: month (YYYY-MM)

response:
{
  "period": "2024-01",
  "categories": [
    {
      "category_id": "uuid",
      "name": "Groceries",
      "budget": 800.00,
      "actual": 743.21,
      "remaining": 56.79,
      "percentage_used": 92.9
    },
    ...
  ]
}
```

Uses the most recent budget row with `effective_from <= period start` and
(`effective_to IS NULL` OR `effective_to >= period end`) for each category.

### Property P&L (Amendment 3)

```
GET /api/v1/reports/property-pnl
  query: property_id, from, to

response:
{
  "property_id": "uuid",
  "nickname": "123 Oak Street",
  "address": "123 Oak Street ...",  // decrypted
  "period": { "from": "2024-01-01", "to": "2024-12-31" },
  "gross_income": 24000.00,
  "total_expenses": 14320.00,
  "net_income": 9680.00,
  "net_yield_pct": 2.31,  // net_income / current_estimated_value * 100
  "expense_breakdown": [
    { "category_id": "uuid", "name": "Mortgage interest", "amount": 8400.00 },
    ...
  ],
  "monthly_series": [
    { "period": "2024-01", "income": 2000.00, "expenses": 1200.00, "net": 800.00 },
    ...
  ]
}
```

Income: transactions where `real_estate_property_id = property_id`
and `category.is_income = TRUE`.
Expenses: transactions where `real_estate_property_id = property_id`
and `category.is_income = FALSE`.

---

## Budget endpoints

```
GET    /api/v1/budgets
  query: period?, category_id?, effective_date?
POST   /api/v1/budgets
  body: {category_id, period, amount, effective_from, effective_to?}
PATCH  /api/v1/budgets/{id}
DELETE /api/v1/budgets/{id}
```

---

## Dashboard

`GET /api/v1/dashboard` — aggregates data for the summary page.

```json
{
  "net_worth": {
    "current": 173000.00,
    "change_30d": 3410.00,
    "change_30d_pct": 2.01
  },
  "cash_flow_mtd": {
    "income": 11250.00,
    "expenses": 7840.00,
    "net": 3410.00
  },
  "top_spending_categories": [ ... ],  // top 5 by MTD spend
  "budget_alerts": [                   // categories > 90% of budget
    { "category": "Dining out", "used_pct": 94.2 }
  ],
  "accounts_summary": {
    "total_assets": 485000.00,
    "total_liabilities": 312000.00
  }
}
```

---

## Audit log UI

### Settings > Activity log

`GET /api/v1/audit-log`
```
query: entity_type?, user_id?, from?, to?, page, page_size (default 50)
requires: primary role
```

Frontend renders a chronological feed. Human-readable descriptions are
generated client-side from `action` + `previous_value` + `new_value`:

```typescript
function describeAuditEvent(event: AuditLogEntry): string {
  const actor = event.user_display_name ?? "System";
  switch (event.action) {
    case "transaction.category_changed":
      return `${actor} changed category on "${event.context?.payee}" `
           + `from ${event.previous_value?.category_name} `
           + `to ${event.new_value?.category_name}`;
    case "member.role_changed":
      return `${actor} changed ${event.context?.member_name}'s role `
           + `from ${event.previous_value?.role} to ${event.new_value?.role}`;
    // ... etc
  }
}
```

The API enriches audit log rows with `user_display_name` and `context`
(entity nickname/payee/etc.) by joining at query time — not stored in
the audit log itself.

### Settings > Security log

`GET /api/v1/audit-log?entity_type=auth`
Filtered to auth events. Accessible to all authenticated users for their
own events. Primary members see all users' auth events.

### Per-record history panel

On transaction detail (`/accounts/{id}/transactions/{txn_id}`) and
account detail pages, a "History" collapsible section queries:

`GET /api/v1/audit-log?entity_type=transaction&entity_id={txn_id}`

Renders oldest-first as a timeline.

---

## Frontend — Phase 3 pages

### `/` (Dashboard)

Four metric cards (net worth, MTD income, MTD expenses, savings rate),
net worth trend chart (12-month line), spending by category donut chart,
budget alert chips.

### `/reports/net-worth`

Line chart with stacked area breakdown (assets by type vs liabilities).
Date range picker. Toggle between monthly/quarterly/annual.

### `/reports/cash-flow`

Grouped bar chart (income vs expenses) with net line overlay.
Month-by-month table below chart with savings rate column.

### `/reports/spending`

Donut chart + ranked list. Click a category to drilldown to subcategories.
Month/quarter/year/custom date range selector.

### `/budgets`

Budget list grouped by category. Inline progress bars (actual vs budget).
"Add budget" button. Current month selector.

### `/properties/{id}`

Property detail page with two tabs:
- Valuation history (line chart of `property_valuations` over time)
  with "Update manually" button and source badge on latest value.
- P&L (date range selector, gross/net cards, expense breakdown bar chart,
  monthly series table).

### `/settings/activity`

Audit event feed (primary only). Filterable by member, entity type, date.

### `/settings/security`

Auth event log. Shows own events for all users; all events for primaries.

---

## Acceptance criteria

1. `GET /api/v1/reports/net-worth` returns a monthly series with correct
   asset/liability breakdown using test fixture data.
2. Transfer transactions are excluded from cash flow income and expense totals.
3. `GET /api/v1/reports/property-pnl` returns correct net income when
   transactions are tagged to a property.
4. `GET /api/v1/reports/budget-vs-actuals` correctly uses the most recent
   effective budget row (not all rows for a category).
5. `GET /api/v1/audit-log` returns 403 for partner and dependent roles.
6. Dashboard loads in under 500ms on a household with 2 years of transaction data.
7. Net worth chart renders correctly with accounts that have no snapshots
   (falls back to running transaction balance).
8. Budget alerts correctly surface categories > 90% used.
9. Per-record history panel on a transaction shows all audit events for
   that transaction in chronological order.
10. Property P&L tab renders for a property with at least one tagged income
    and one tagged expense transaction.
