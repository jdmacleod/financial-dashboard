# API Reference

All endpoints are under `/api/v1/`. The base URL for a local installation is `http://localhost/api/v1`.

## Authentication

Most endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire in 30 minutes by default. Use the refresh endpoint to obtain a new access token using the `refresh_token` HttpOnly cookie set at login.

---

## Setup

### `GET /setup/status`

Returns whether the initial household setup has been completed.

**Response:**

```json
{ "setup_complete": true }
```

### `POST /setup`

Creates the household, the primary member, and the first user account. Only available before setup is complete.

**Request body:**

```json
{
  "household_name": "Smith Family",
  "member_name": "Alex",
  "email": "alex@example.com",
  "password": "<password>"
}
```

**Response:** `TokenResponse` — an access token is returned and a `refresh_token` HttpOnly cookie is set.

---

## Authentication

### `POST /auth/login`

**Request body:**

```json
{ "email": "alex@example.com", "password": "<password>" }
```

**Response:**

```json
{ "access_token": "<jwt>" }
```

Sets `refresh_token` HttpOnly cookie.

**Errors:** `401` — invalid credentials. `423` — account locked after too many failed attempts.

### `POST /auth/refresh`

Exchanges the `refresh_token` cookie for a new access token. Rotates the refresh token.

**Response:** `TokenResponse`

### `POST /auth/logout`

Invalidates the current refresh token and clears the cookie.

**Response:** `204 No Content`

### `POST /auth/reauth`

Re-authenticates the current user and returns a short-lived `reauth_token` used to authorize sensitive operations (e.g. exports).

**Request body:**

```json
{ "password": "<password>" }
```

**Response:**

```json
{ "reauth_token": "<short-lived-jwt>" }
```

### `POST /auth/change-password`

Changes the current user's password. Invalidates all existing refresh tokens.

**Request body:**

```json
{
  "current_password": "<current-password>",
  "new_password": "<new-password>"
}
```

**Response:** `204 No Content`

---

## Household

### `GET /household`

Returns the household record.

**Response:**

```json
{
  "id": "uuid",
  "name": "Smith Family",
  "settings": {}
}
```

### `PATCH /household`

Updates the household name or settings. Primary only.

**Request body (all fields optional):**

```json
{
  "name": "The Smith Household",
  "settings": {}
}
```

### `GET /settings/valuation-provider`

Returns the current real estate valuation configuration. Primary only.

**Response:**

```json
{
  "provider": "manual",
  "has_api_key": false
}
```

### `PATCH /settings/valuation-provider`

Updates the valuation provider and API key. Writes to `.env` so the change survives restarts. Primary only.

**Request body:**

```json
{
  "provider": "attom",
  "api_key": "<your-api-key>"
}
```

Valid providers: `manual`, `attom`, `estated`.

---

## Members

### `GET /members`

Lists all household members.

**Response:** array of `MemberResponse`

```json
[
  {
    "id": "uuid",
    "name": "Alex",
    "role": "primary",
    "is_active": true,
    "settings": { "dashboard_widgets": [] }
  }
]
```

### `POST /members`

Creates a new member. Primary only.

**Request body:**

```json
{
  "name": "Jordan",
  "role": "partner",
  "email": "jordan@example.com",
  "password": "<password>"
}
```

### `GET /members/{member_id}`

Returns a single member.

### `PATCH /members/{member_id}`

Updates a member's name or role. Primary only.

**Request body (all optional):**

```json
{ "name": "Jordan Smith", "role": "dependent" }
```

### `PATCH /members/{member_id}/dashboard-layout`

Updates the dashboard widget configuration for a member. Members can only update their own layout.

**Request body:**

```json
{
  "widgets": [
    { "id": "metric_cards", "visible": true, "order": 0 },
    { "id": "budget_alerts", "visible": true, "order": 1 },
    { "id": "net_worth_chart", "visible": true, "order": 2 },
    { "id": "spending_chart", "visible": false, "order": 3 }
  ]
}
```

Valid widget IDs: `metric_cards`, `budget_alerts`, `net_worth_chart`, `spending_chart`.

### `DELETE /members/{member_id}`

Deactivates a member. Primary only. Cannot deactivate the primary member.

**Response:** `204 No Content`

---

## Users

### `GET /users/me`

Returns the current user's profile.

**Response:**

```json
{
  "id": "uuid",
  "email": "alex@example.com",
  "member_id": "uuid",
  "is_active": true
}
```

---

## Accounts

### `GET /accounts`

Lists all accounts visible to the current member (based on role and access grants).

**Response:** array of `AccountResponse`

```json
[
  {
    "id": "uuid",
    "name": "Chase Checking",
    "type": "checking",
    "institution_name": "Chase Bank",
    "account_number_last4": "1234",
    "is_active": true,
    "owner_member_id": "uuid"
  }
]
```

Account types: `checking`, `savings`, `credit`, `investment`, `retirement`, `loan`.

### `POST /accounts`

Creates an account owned by the current member.

**Request body:**

```json
{
  "name": "Chase Checking",
  "type": "checking",
  "institution_name": "Chase Bank",
  "account_number": "123456781234",
  "routing_number": "021000021",
  "notes": "Primary checking account"
}
```

Sensitive fields (`institution_name`, `account_number`, `routing_number`, `notes`) are stored encrypted.

**Response:** `AccountResponse` — `201 Created`

### `GET /accounts/{account_id}`

Returns a single account.

### `PATCH /accounts/{account_id}`

Updates an account. All fields optional.

**Request body:**

```json
{
  "name": "Chase Checking (joint)",
  "notes": "Updated notes"
}
```

### `DELETE /accounts/{account_id}`

Deactivates an account. Transactions are preserved.

**Response:** `204 No Content`

### `GET /accounts/{account_id}/grants`

Lists access grants for an account.

**Response:**

```json
[
  {
    "id": "uuid",
    "account_id": "uuid",
    "member_id": "uuid",
    "created_at": "2025-01-15T10:00:00Z"
  }
]
```

### `POST /accounts/{account_id}/grants`

Grants read access to a member. Primary only.

**Request body:**

```json
{ "member_id": "uuid" }
```

### `DELETE /accounts/{account_id}/grants/{grant_id}`

Revokes an access grant. Primary only.

**Response:** `204 No Content`

---

## Transactions

### `GET /accounts/{account_id}/transactions`

Lists transactions for an account with optional filtering and pagination.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `from` | date | Filter from date (ISO 8601, inclusive) |
| `to` | date | Filter to date (ISO 8601, inclusive) |
| `category_id` | uuid | Filter by category |
| `is_reviewed` | bool | Filter by review status |
| `is_transfer` | bool | Filter by transfer flag |
| `real_estate_property_id` | uuid | Filter by linked property |
| `search` | string | Full-text search on memo/description |
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 50, max: 500) |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "date": "2025-01-15",
      "amount": "-42.5000",
      "memo": "Whole Foods Market",
      "category_id": "uuid",
      "is_reviewed": false,
      "is_transfer": false,
      "real_estate_property_id": null
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 50
}
```

Amounts are `NUMERIC(18,4)` strings. Negative = debit/expense; positive = credit/income for checking/savings. For credit accounts the convention is reversed (positive = charge, negative = payment).

### `POST /accounts/{account_id}/transactions`

Creates a transaction.

**Request body:**

```json
{
  "date": "2025-01-15",
  "amount": "-42.5000",
  "memo": "Whole Foods Market",
  "category_id": "uuid",
  "is_transfer": false,
  "real_estate_property_id": null
}
```

**Response:** `TransactionResponse` — `201 Created`

### `GET /transactions/{transaction_id}`

Returns a single transaction by ID (account-agnostic lookup).

### `PATCH /transactions/{transaction_id}`

Updates a transaction. All fields optional.

**Request body:**

```json
{
  "category_id": "uuid",
  "memo": "Updated memo",
  "is_reviewed": true
}
```

### `DELETE /transactions/{transaction_id}`

Deletes a transaction permanently.

**Response:** `204 No Content`

### `PATCH /accounts/{account_id}/transactions/bulk-categorize`

Assigns a category to multiple transactions at once.

**Request body:**

```json
{
  "transaction_ids": ["uuid1", "uuid2", "uuid3"],
  "category_id": "uuid"
}
```

**Response:** array of updated `TransactionResponse`

---

## Categories

### `GET /categories`

Lists all categories for the household.

**Response:**

```json
[
  {
    "id": "uuid",
    "name": "Food & Dining",
    "parent_id": null,
    "color": "#10b981"
  },
  {
    "id": "uuid",
    "name": "Groceries",
    "parent_id": "parent-uuid",
    "color": "#3b82f6"
  }
]
```

### `POST /categories`

Creates a category.

**Request body:**

```json
{
  "name": "Groceries",
  "parent_id": "uuid",
  "color": "#3b82f6"
}
```

### `PATCH /categories/{category_id}`

Updates a category. All fields optional.

### `DELETE /categories/{category_id}`

Deletes a category. Transactions referencing it have their `category_id` set to `null`.

**Response:** `204 No Content`

---

## Budgets

### `GET /budgets`

Lists budgets with optional filtering.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `category_id` | uuid | Filter to a specific category |
| `effective_date` | date | Returns budgets effective on or before this date |

**Response:**

```json
[
  {
    "id": "uuid",
    "category_id": "uuid",
    "monthly_limit": "500.0000",
    "effective_from": "2025-01-01",
    "effective_to": null
  }
]
```

### `POST /budgets`

Creates a budget.

**Request body:**

```json
{
  "category_id": "uuid",
  "monthly_limit": "500.0000",
  "effective_from": "2025-01-01",
  "effective_to": null
}
```

### `PATCH /budgets/{budget_id}`

Updates a budget's monthly limit or effective date.

### `DELETE /budgets/{budget_id}`

Deletes a budget.

**Response:** `204 No Content`

---

## Snapshots

Snapshots record the balance of investment and retirement accounts at a point in time.

### `GET /accounts/{account_id}/snapshots`

Lists snapshots for an account, newest first.

**Response:**

```json
[
  {
    "id": "uuid",
    "account_id": "uuid",
    "date": "2025-01-01",
    "balance": "87450.0000"
  }
]
```

### `POST /accounts/{account_id}/snapshots`

Records a balance snapshot.

**Request body:**

```json
{
  "date": "2025-01-01",
  "balance": "87450.0000"
}
```

### `PATCH /accounts/{account_id}/snapshots/{snapshot_id}`

Updates a snapshot balance or date.

### `DELETE /accounts/{account_id}/snapshots/{snapshot_id}`

Deletes a snapshot.

**Response:** `204 No Content`

---

## Imports

### `POST /accounts/{account_id}/import/preview`

Parses an uploaded file and returns a preview without creating an import job. Send as `multipart/form-data` with a `file` field.

**Response:**

```json
{
  "format": "csv",
  "record_count": 48,
  "columns": ["Date", "Description", "Amount"],
  "sample_rows": [...]
}
```

### `POST /accounts/{account_id}/import`

Starts an import job. Send as `multipart/form-data`.

**Form fields:**
| Field | Type | Description |
|---|---|---|
| `file` | file | CSV or OFX/QFX file |
| `mapping` | string (JSON) | Optional column mapping for CSV files |

**Response:** `ImportJobResponse` — `201 Created`

```json
{
  "id": "uuid",
  "account_id": "uuid",
  "filename": "chase_jan_2025.csv",
  "format": "csv",
  "status": "pending",
  "records_found": null,
  "records_imported": null,
  "error_message": null,
  "created_at": "2025-01-15T10:00:00Z"
}
```

### `GET /import-jobs/{job_id}`

Returns a single import job.

### `GET /import-jobs`

Lists all import jobs for the household, newest first.

---

## Reports

### `GET /reports/net-worth`

Net worth over time.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `from` | date | Start date (required) |
| `to` | date | End date (required) |
| `interval` | string | `monthly` \| `quarterly` \| `annual` (default: `monthly`) |

**Response:**

```json
{
  "series": [
    {
      "date": "2025-01-01",
      "total_assets": "250000.0000",
      "total_liabilities": "180000.0000",
      "net_worth": "70000.0000",
      "breakdown": {
        "checking_savings": "24500.0000",
        "investment": "148000.0000",
        "retirement": "201000.0000",
        "real_estate": "420000.0000",
        "hsa": "8200.0000",
        "other_assets": "0.0000",
        "mortgage": "-298000.0000",
        "other_liabilities": "-14000.0000"
      }
    }
  ],
  "current": {
    "date": "2025-01-01",
    "total_assets": "250000.0000",
    "total_liabilities": "180000.0000",
    "net_worth": "70000.0000",
    "breakdown": { "...": "..." }
  }
}
```

### `GET /reports/cash-flow`

Income and expenses over time.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `from` | date | Start date (required) |
| `to` | date | End date (required) |
| `group_by` | string | `month` \| `quarter` (default: `month`) |

**Response:**

```json
{
  "series": [
    {
      "period": "2025-01",
      "income": "5800.0000",
      "expenses": "3200.0000",
      "net": "2600.0000",
      "savings_rate": 44.8
    }
  ],
  "totals": {
    "income": "5800.0000",
    "expenses": "3200.0000",
    "net": "2600.0000",
    "savings_rate": 44.8
  }
}
```

### `GET /reports/spending-by-category`

Spending totals per category.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `from` | date | Start date (required) |
| `to` | date | End date (required) |
| `parent_category_id` | uuid | Filter to subcategories of a parent |

**Response:**

```json
{
  "total": "-3490.0000",
  "categories": [
    {
      "category_id": "uuid",
      "name": "Groceries",
      "amount": "-642.5000",
      "percentage": 18.4,
      "transaction_count": 14,
      "has_children": false
    }
  ]
}
```

### `GET /reports/budget-vs-actuals`

Budget vs. actual spending for a month.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `month` | string | Month in `YYYY-MM` format (required) |

**Response:**

```json
{
  "period": "2025-01",
  "categories": [
    {
      "category_id": "uuid",
      "name": "Groceries",
      "budget": "500.0000",
      "actual": "642.5000",
      "remaining": "-142.5000",
      "percentage_used": 128.5
    }
  ]
}
```

### `GET /reports/property-pnl`

Income vs. expenses for a real estate property.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `property_id` | uuid | Property ID (required) |
| `from` | date | Start date (required) |
| `to` | date | End date (required) |

### `GET /dashboard`

Aggregated dashboard data: net worth summary, MTD cash flow, budget alerts, and top spending categories.

**Response:**

```json
{
  "net_worth": {
    "current": "125000.0000",
    "change_30d": "2500.0000",
    "change_30d_pct": 2.04
  },
  "cash_flow_mtd": {
    "income": "5800.0000",
    "expenses": "3200.0000",
    "net": "2600.0000"
  },
  "budget_alerts": [{ "category": "Dining Out", "used_pct": 92.3 }],
  "top_spending_categories": [{ "name": "Groceries", "amount": "-642.5000" }],
  "accounts_summary": {
    "total_assets": "675200.0000",
    "total_liabilities": "312000.0000"
  }
}
```

---

## FIRE Scenarios

### `GET /fire-scenarios`

Lists all FIRE scenarios for the household.

**Response:** array of `FireScenarioResponse`

### `POST /fire-scenarios`

Creates a FIRE scenario.

**Request body:**

```json
{
  "name": "Lean FIRE at 45",
  "target_annual_spend": "48000.00",
  "safe_withdrawal_rate": "0.0400",
  "expected_annual_return": "0.0700",
  "expected_inflation_rate": "0.0300",
  "target_retirement_age": 45,
  "additional_income_streams": [
    {
      "id": "client-generated-uuid",
      "label": "Salary",
      "type": "salary",
      "amount_annual": "95000.00",
      "growth_rate_annual": "0.0300",
      "start_year": 2025,
      "end_year": 2040,
      "is_pre_retirement": true,
      "notes": null,
      "real_estate_property_id": null
    },
    {
      "id": "client-generated-uuid",
      "label": "Social Security",
      "type": "social_security",
      "amount_annual": "18000.00",
      "growth_rate_annual": "0.0200",
      "start_year": 2055,
      "end_year": null,
      "is_pre_retirement": false,
      "notes": null,
      "real_estate_property_id": null
    }
  ]
}
```

Income stream `type` values: `salary`, `rental`, `consulting`, `pension`, `social_security`, `investment`, `other`.

Safe withdrawal rate defaults to `0.04` (4%) if omitted. Expected return defaults to `0.07` (7%); inflation defaults to `0.03` (3%).

**Response:** `FireScenarioResponse` — `201 Created`

```json
{
  "id": "uuid",
  "name": "Lean FIRE at 45",
  "target_annual_spend": "48000.00",
  "safe_withdrawal_rate": "0.0400",
  "expected_annual_return": "0.0700",
  "expected_inflation_rate": "0.0300",
  "target_retirement_age": 45,
  "additional_income_streams": [
    {
      "id": "uuid",
      "label": "Salary",
      "type": "salary",
      "amount_annual": "95000.00",
      "growth_rate_annual": "0.0300",
      "start_year": 2025,
      "end_year": 2040,
      "is_pre_retirement": true,
      "notes": null,
      "real_estate_property_id": null,
      "auto_detected": false,
      "detected_at": null
    }
  ],
  "detected_savings_rate": null,
  "detected_portfolio_value": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

### `GET /fire-scenarios/{scenario_id}`

Returns a single scenario.

**Response:** `FireScenarioResponse`

### `PATCH /fire-scenarios/{scenario_id}`

Updates a scenario. All fields optional.

**Request body (example):**

```json
{
  "name": "Lean FIRE at 47",
  "target_annual_spend": "52000.00",
  "safe_withdrawal_rate": "0.0350"
}
```

**Response:** `FireScenarioResponse`

### `DELETE /fire-scenarios/{scenario_id}`

Deletes a scenario.

**Response:** `204 No Content`

### `POST /fire-scenarios/{scenario_id}/detect`

Runs `FireInputDetector` against the member's transaction history and merges the results into the scenario. Auto-detected income streams are added or updated; manually-entered streams are preserved.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `trailing_months` | int | Months of history to analyse (default: 12, range: 1–60) |

**Response:** `FireDetectionResponse`

```json
{
  "scenario": {
    "id": "uuid",
    "name": "Lean FIRE at 45",
    "target_annual_spend": "48000.00",
    "safe_withdrawal_rate": "0.0400",
    "expected_annual_return": "0.0700",
    "expected_inflation_rate": "0.0300",
    "target_retirement_age": 45,
    "additional_income_streams": [
      {
        "id": "uuid",
        "label": "Payroll",
        "type": "salary",
        "amount_annual": "96000.00",
        "growth_rate_annual": "0.0300",
        "start_year": 2026,
        "end_year": null,
        "is_pre_retirement": true,
        "notes": null,
        "real_estate_property_id": null,
        "auto_detected": true,
        "detected_at": "2026-06-18T10:00:00Z"
      }
    ],
    "detected_savings_rate": "0.3200",
    "detected_portfolio_value": "125000.0000",
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2026-06-18T10:00:00Z"
  },
  "warnings": [
    "Only 5 months of transaction data available. Detected values may not reflect your typical financial picture."
  ]
}
```

Income streams are returned under `scenario.additional_income_streams`. The `warnings` array is empty when detection ran normally (12+ months of data). Auto-detected streams have `auto_detected: true` and a `detected_at` timestamp.

### `GET /fire-scenarios/{scenario_id}/projection`

Returns a year-by-year FIRE projection using the scenario's income streams, portfolio value, and rate assumptions.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `from_year` | int | First year of the projection (default: current year) |

**Response:** `FireProjectionResponse`

```json
{
  "summary": {
    "fire_year": 2041,
    "fire_age": 52,
    "years_to_fire": 15,
    "fire_number": "1200000.00",
    "headline": "FIRE in 15 years at age 52"
  },
  "projections": [
    {
      "year": 2026,
      "age": 37,
      "portfolio": "125000.0000",
      "annual_income": "96000.00",
      "annual_spend": "48000.00",
      "annual_savings": "48000.00",
      "supplemental_income": "0.00",
      "effective_withdrawal": "48000.00",
      "fire_number": "1200000.00",
      "is_fire_year": false
    }
  ]
}
```

`summary.fire_number` is computed as `target_annual_spend / safe_withdrawal_rate`. `fire_age` and `years_to_fire` are `null` when no FIRE crossing is found within the 75-year projection horizon. `age` per projection row is `null` if the primary member's date of birth is not recorded.

---

## Debt Payoff

### `GET /debt-payoff`

Returns a side-by-side avalanche and snowball payoff analysis for all loan and credit accounts, with an optional extra monthly payment applied.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `extra_monthly_payment` | decimal | Additional monthly payment applied on top of all minimums (default: `0`) |
| `strategy` | string | `avalanche` or `snowball` — if supplied, only that plan is computed; both are returned when omitted |

**Response:** `DebtPayoffComparisonResponse`

```json
{
  "debts": [
    {
      "account_id": "uuid",
      "name": "Chase Credit Card",
      "balance": "4500.0000",
      "interest_rate": "0.2199",
      "monthly_minimum": "90.0000"
    },
    {
      "account_id": "uuid",
      "name": "Student Loan",
      "balance": "12000.0000",
      "interest_rate": "0.0650",
      "monthly_minimum": "130.0000"
    }
  ],
  "avalanche": {
    "strategy": "avalanche",
    "months_to_payoff": 62,
    "total_interest_paid": "2100.0000",
    "payoff_date": "2031-08-01",
    "payoff_order": ["Chase Credit Card", "Student Loan"],
    "monthly_series": [
      {
        "month": 1,
        "date": "2026-07-01",
        "total_remaining": "16280.0000",
        "per_debt": {
          "uuid-chase": "4280.0000",
          "uuid-student": "12000.0000"
        }
      }
    ]
  },
  "snowball": {
    "strategy": "snowball",
    "months_to_payoff": 64,
    "total_interest_paid": "2350.0000",
    "payoff_date": "2031-10-01",
    "payoff_order": ["Chase Credit Card", "Student Loan"],
    "monthly_series": [...]
  }
}
```

**Strategies:**

- **Avalanche** — directs extra payment to the highest-interest-rate debt first. Minimises total interest paid.
- **Snowball** — directs extra payment to the lowest-balance debt first. Provides earlier psychological wins as individual debts clear sooner.

When a debt reaches $0 its former minimum payment is automatically rolled into the extra pool for the next target debt.

---

## Real Estate

### `POST /properties`

Creates a real estate property.

**Request body:**

```json
{
  "address": "123 Main St, Springfield, IL 62701",
  "purchase_date": "2020-06-01",
  "purchase_price": "285000.0000",
  "current_value": "320000.0000"
}
```

The `address` field is stored encrypted.

**Response:** `PropertyResponse` — `201 Created`

### `GET /properties/{property_id}`

Returns a property.

### `PATCH /properties/{property_id}`

Updates a property.

### `GET /properties/{property_id}/valuations`

Lists valuations for a property, newest first.

### `POST /properties/{property_id}/valuations`

Adds a manual valuation.

**Request body:**

```json
{
  "date": "2025-01-01",
  "value": "335000.0000",
  "source": "manual"
}
```

---

## Exports

### `POST /exports`

Creates an export job. Requires a `X-Reauth-Token` header obtained from `POST /auth/reauth`.

**Request headers:**

```
X-Reauth-Token: <reauth_token>
```

**Request body:**

```json
{
  "export_type": "pdf_net_worth",
  "params": {
    "from": "2024-01-01",
    "to": "2025-01-01",
    "interval": "monthly"
  }
}
```

Export types: `pdf_net_worth`, `pdf_cash_flow`, `pdf_spending`, `xlsx_transactions`, `xlsx_net_worth`.

**Response:** `201 Created`

```json
{ "export_job_id": "uuid" }
```

### `GET /exports`

Lists export jobs.

### `GET /exports/{job_id}`

Returns an export job.

### `GET /exports/{job_id}/download`

Downloads the export file once status is `complete`. Returns the file with the appropriate content type (`application/pdf` or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`).

---

## Backups

### `GET /backups`

Lists backup jobs, newest first. Primary only.

**Response:** array of `BackupJobResponse`

```json
[
  {
    "id": "uuid",
    "triggered_by": "manual",
    "triggered_by_user_id": "uuid",
    "status": "complete",
    "filename": "backup-2025-01-15T02-00-00Z.dump.enc",
    "file_size_bytes": 1048576,
    "error_message": null,
    "started_at": "2025-01-15T02:00:00Z",
    "completed_at": "2025-01-15T02:00:12Z"
  }
]
```

### `POST /backups`

Triggers a manual backup job. Primary only.

**Response:** `BackupJobResponse` — `201 Created`

### `GET /backups/{job_id}/download`

Downloads the backup file for a completed job. Primary only. Returns `404` if the job is not yet complete.

---

## Audit Log

### `GET /audit-log`

Returns the household audit log. Access control: primary members see all events; partners and dependents may only query per-record history for entities they can see; all users can see their own auth events.

**Query parameters:**
| Parameter | Type | Description |
|---|---|---|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Results per page (default: 50, max: 200) |
| `member_id` | uuid | Filter by actor member |
| `user_id` | uuid | Filter by actor user |
| `entity_type` | string | Filter by entity type (e.g. `account`, `transaction`) |
| `entity_id` | uuid | Filter to a single record's history |
| `from` | datetime | Start of date range (ISO 8601) |
| `to` | datetime | End of date range (ISO 8601) |

**Response:**

```json
{
  "items": [
    {
      "id": "uuid",
      "created_at": "2025-01-15T10:00:00Z",
      "actor_member_id": "uuid",
      "entity_type": "transaction",
      "entity_id": "uuid",
      "action": "update",
      "previous_value": { "category_id": null },
      "new_value": { "category_id": "uuid" },
      "ip_address": "192.168.1.1"
    }
  ],
  "total": 482,
  "page": 1,
  "page_size": 50
}
```

---

## Error responses

All errors follow this shape:

```json
{ "detail": "Human-readable error message" }
```

Common status codes:
| Code | Meaning |
|---|---|
| `400` | Invalid request (validation error or bad parameters) |
| `401` | Not authenticated or token expired |
| `403` | Authenticated but not authorized for this action |
| `404` | Resource not found |
| `409` | Conflict (e.g. duplicate import) |
| `422` | Pydantic validation failure (field-level errors in `detail`) |
| `423` | Account locked (too many failed login attempts) |
| `500` | Internal server error |
