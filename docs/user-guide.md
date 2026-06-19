# User Guide

This guide covers every feature in HearthLedger. If you haven't installed it yet, start with [Getting Started](getting-started.md).

---

## Dashboard

The dashboard shows a real-time summary of your household finances.

**Widgets:**

- **KPI Cards** — net worth, MTD income, MTD expenses, savings rate
- **Budget Alerts** — categories that have exceeded 90% of their monthly budget
- **Net Worth Chart** — trailing 12-month trend line
- **Spending by Category** — current month, donut chart

**Customizing the layout:**
Click the **Customize →** link in the top-right of the dashboard, or go to **Settings → Dashboard Layout**. You can toggle each widget on/off and reorder them with the ▲/▼ buttons. Click **Save layout** — preferences are stored per-member, so each household member can have their own layout.

---

## Accounts

Accounts represent financial accounts: checking, savings, credit cards, investment accounts, retirement accounts, and loans.

**Creating an account:**

1. Go to **Accounts** in the sidebar.
2. Click **New account**.
3. Set the name, type, institution, and optionally the account number.
4. Click **Save**.

Account types:
| Type | Description |
|---|---|
| `checking` | Everyday transactional account |
| `savings` | Interest-bearing savings |
| `credit` | Credit card (balance is a liability) |
| `investment` | Brokerage, taxable investing |
| `retirement` | 401k, 403b, IRA, Roth IRA |
| `pension` | Defined-benefit pension plan — see [Pension accounts](#pension-accounts) below |
| `hsa` | Health savings account |
| `real_estate` | Real estate property — see [Real Estate](#real-estate) |
| `mortgage` | Mortgage (balance is a liability) |
| `loan` | Auto loan, student loan, personal loan |

**Access grants (partner visibility):**
By default, partner members can only see accounts they own. The primary member can grant read access to an account: go to the account detail page and click **Manage access** to add or remove grants.

**Balances for investment/retirement accounts:**
Rather than individual holdings, HearthLedger uses balance snapshots. Go to the account's **Snapshots** tab and record a balance as of a date. The net worth calculation uses the most recent snapshot.

**Deactivating an account:**
Click the **…** menu on an account and choose **Deactivate**. Deactivated accounts are hidden from lists but historical data is preserved.

---

## Pension accounts

When you create an account of type `pension`, a **Pension details** card appears on the account page. Click **Add pension details** (or the pencil icon) to record:

| Field                        | Description                                                              |
| ---------------------------- | ------------------------------------------------------------------------ |
| **Plan name**                | Name of the plan (e.g. "State Teachers Pension Fund") — stored encrypted |
| **Administrator**            | Plan administrator name — stored encrypted                               |
| **Monthly benefit estimate** | Estimated monthly payout in retirement                                   |
| **Eligibility age / date**   | When you can start drawing — set one or the other                        |
| **COLA adjustment rate**     | Annual cost-of-living increase rate (default 2%)                         |
| **Vested**                   | Toggle on when vesting requirements are met                              |
| **Vesting date**             | Date vesting was achieved                                                |
| **Survivor benefit %**       | Survivor benefit as a percentage (0–100%)                                |
| **Notes**                    | Free-form notes — stored encrypted                                       |

The account's transaction list shows a **Defined-benefit summary card** above the transactions, with plan name, monthly benefit, eligibility info, and vested status. If no detail record exists yet, a prompt to "Add pension details →" is shown.

The FIRE detector automatically creates a `pension` income stream for each vested pension with a non-zero monthly benefit estimate. See [Auto-detect income streams](#auto-detect-income-streams).

---

## Transactions

### Browsing transactions

Click an account name to open its transaction list. You can filter by:

- Date range
- Category
- Review status
- Transfer flag
- Free-text search (memo/description)

Pagination defaults to 50 per page (up to 500 per page via the `page_size` query parameter).

### Adding a transaction manually

Click **New entry** and fill in the date, amount, payee, memo, and optional category. The category field pre-selects a sensible default based on the account type — retirement accounts (401k, 403b, IRA, Roth IRA) default to "Contributions"; pension accounts default to "Income".

### Editing a transaction

Click the pencil icon on any transaction row to open a pre-filled edit form. You can update the date, amount, payee, memo, and category. Changes are saved immediately via PATCH.

### Deleting a transaction

Click the trash icon on any transaction row. A confirmation dialog appears before the delete is sent. If the delete fails, the dialog stays open and shows an inline error rather than closing silently.

### Importing transactions

Click **Import** on an account, then drag a file onto the uploader.

**Supported formats:**

- **CSV** — most banks export in this format. Required columns depend on the bank; use the column-mapping step if the importer asks you to match fields.
- **OFX / QFX** — native financial data exchange format; no mapping needed.

The import runs as a background job. Watch the **Settings → Import History** page to track progress.

**Duplicate detection:** transactions already in the account (matched by OFX `FITID` for OFX imports, or by date+amount+memo for CSV) are skipped automatically.

### Reviewing transactions

Unreviewed transactions are shown with a dim indicator. Click a transaction row to open it, then click **Mark reviewed**. Use bulk-categorize to assign categories to multiple transactions at once.

### Bulk categorize

Select multiple transactions by clicking their checkboxes, then use the **Categorize** dropdown in the toolbar. The selected transactions are all assigned the chosen category in one request.

---

## Categories

Categories organize your spending. HearthLedger supports two levels: parent categories (e.g. "Food & Dining") and child categories (e.g. "Groceries", "Restaurants").

**Creating a category:**

1. Go to **Categories** in the sidebar.
2. Click **New category**.
3. Enter the name and optionally choose a parent category.
4. Click **Save**.

Deleting a category with assigned transactions will unset the category on those transactions (it does not delete the transactions themselves).

---

## Budgets

Budgets set monthly spending targets per category.

**Creating a budget:**

1. Go to **Budgets** in the sidebar.
2. Click **New budget**.
3. Choose a category and set the monthly limit.
4. Optionally set an `effective_from` date — budgets take effect from that date forward. An `effective_to` date can also be set to retire a budget at a future date without deleting it.

The dashboard shows budget alerts for categories that have exceeded 90% of their limit. The **Budget vs Actuals** report (under Reports) shows a full breakdown for any month.

---

## Reports

All reports are under the **Reports** menu in the top navigation.

### Net Worth

Shows total assets, total liabilities, and net worth over time. Configure:

- **Date range** — start and end date
- **Interval** — monthly, quarterly, or annual

Assets include: account balances + property valuations. Liabilities include: credit card balances + loan balances.

**Pension annotations:** Below the net worth chart, each pension account with a defined monthly benefit estimate is listed with annual benefit, eligibility info, and a **Show PV** toggle. Toggling on converts the annual benefit stream to present value using a 4% discount rate, giving you a sense of the economic value of the pension alongside your portfolio.

### Cash Flow

Shows income and expenses grouped by time period. Configure:

- **Date range**
- **Group by** — month or quarter

### Spending by Category

Shows spending totals per category for a date range. Optionally filter to a single parent category to drill into subcategories.

### Budget vs Actuals

Shows every category with a budget alongside its actual spending for a given month. Format: `YYYY-MM`, e.g. `2025-01`.

### Property P&L

For a real estate property, shows income (rent transactions linked to the property) vs. expenses (maintenance, taxes, etc.) over a date range. See [Real Estate](#real-estate) for how to link transactions to a property.

---

## FIRE Planning

FIRE (Financial Independence, Retire Early) scenarios let you model retirement timelines based on your current financial position. Go to **FIRE** in the sidebar to manage your scenarios.

### Creating a scenario

Click **New scenario** and fill in:

- **Name** — e.g. "Lean FIRE at 45" or "Coast FIRE"
- **Target annual spend** — estimated annual spending in retirement, in today's dollars
- **Safe withdrawal rate** — the annual percentage you plan to withdraw from your portfolio (default 4%). Your FIRE number is computed as `target_annual_spend ÷ safe_withdrawal_rate`; at 4% and $48,000/year, the FIRE number is $1,200,000
- **Expected annual return** — projected portfolio growth rate (default 7%)
- **Expected inflation rate** — used to inflation-adjust your spend target each year in the projection (default 3%)
- **Target retirement age** (optional) — shown on the projection chart

### Income streams

Each scenario tracks income streams — sources of money that affect your path to FIRE. Add them under the **Income Streams** section of the scenario editor.

Each stream has:
| Field | Description |
|---|---|
| **Label** | Display name, e.g. "Salary", "Rental income" |
| **Type** | `salary`, `rental`, `consulting`, `pension`, `social_security`, `investment`, or `other` |
| **Annual amount** | Gross annual amount in today's dollars |
| **Annual growth rate** | How fast this income grows per year (e.g. `0.03` for 3%) |
| **Start year / End year** | Active range — leave end year blank for indefinite |
| **Pre-retirement?** | Toggle on for income you earn before FIRE; toggle off for post-retirement income (e.g. Social Security, pension). Post-retirement streams reduce your effective withdrawal need rather than boosting savings |
| **Property link** | Rental streams can be linked to a real estate property |

Consulting and other variable-income streams show a yellow "Variable income — review estimate" warning as a reminder to sanity-check the amount.

### Auto-detect income streams

Click **Auto-detect from transactions** to have HearthLedger analyse your actual transaction history and generate income stream entries automatically.

The detector groups your income transactions by category (using the trailing 12 months by default), annualises them, and merges the results into your scenario. It also creates a `pension` income stream for each vested pension account that has a non-zero monthly benefit estimate, using the pension's eligibility age/date as the stream start year and its COLA rate as the annual growth rate. Streams detected this way are marked with a **Detected** badge and a timestamp.

**Important behaviours:**

- Manually-entered streams are never overwritten by detection
- Running detection a second time updates existing auto-detected streams rather than duplicating them
- If fewer than 6 months of transaction data are available, the detection result includes a warning message displayed as a yellow alert banner; you can still use the values but should review them carefully

Change the trailing window (1–60 months) to include more or less history before clicking detect.

### Reading the projection chart

After saving a scenario, the right panel shows the projection chart:

- **Blue line** — projected portfolio value over time, starting from the detected or manually-entered current portfolio value
- **Orange dashed line** — your FIRE number (grows with inflation each year)
- **FIRE crossing annotation** — the year and age at which your portfolio crosses the FIRE number ("FIRE at age 52, 2039")

Below the chart, a year-by-year table shows: year, age, portfolio value, annual income, annual savings, and effective withdrawal amount for each year.

If the projection doesn't cross the FIRE number within 75 years, the chart shows the full 75-year horizon with no crossing annotation.

### Scenario list

The **FIRE** index page (`/fire`) shows all your scenarios as cards. Each card displays the scenario name, target annual spend, and the headline metric from the most recent projection (e.g. "FIRE in 15 years at age 52").

---

## Debt Payoff

Go to **Debt** in the sidebar to see a payoff analysis of all your loan and credit accounts.

### Reading the debt list

The top of the page shows each of your active loan and credit accounts with:

- Current balance
- Interest rate (APR)
- Minimum monthly payment

### Modelling extra payments

Enter an amount in the **Extra monthly payment** field to model paying more than the minimums. Both payoff plans update in real time as you type.

### Avalanche vs Snowball

The page shows both strategies side by side so you can compare them directly.

| Strategy      | How it works                                                  | Best for                                       |
| ------------- | ------------------------------------------------------------- | ---------------------------------------------- |
| **Avalanche** | Directs extra payment to the highest-interest-rate debt first | Minimising total interest paid                 |
| **Snowball**  | Directs extra payment to the lowest-balance debt first        | Motivation — individual debts disappear faster |

When a debt reaches $0, its former minimum payment is automatically redirected to the next target debt (this is the "rollover" or "snowball roll" effect).

### What each plan shows

Each strategy panel shows:

- **Months to payoff** and **Payoff date**
- **Total interest paid** across all debts
- **Payoff order** — the sequence in which individual debts are cleared
- **Balance over time chart** — stacked area chart showing remaining balances by debt month by month

The avalanche strategy will always pay equal or less total interest than snowball when interest rates differ across your debts.

---

## Real Estate

Real estate properties are tracked under **Properties** in the sidebar.

### Adding a property

Click **New property** and enter:

- Address (stored encrypted)
- Property type: Primary Residence, Rental, Vacation, Commercial, Land, or Other
- Purchase date and price
- Current estimated value (or use a valuation provider — see below)

The property type is displayed on the account list and transaction list banner, and is also available in the Property P&L report.

### Manual valuations

On the property detail page, click **Add valuation** to record an estimated market value as of a date. The most recent valuation is used in net worth calculations.

### Automated valuations (ATTOM / Estated)

If you have an API key from ATTOM Data Solutions or Estated, configure it under **Settings → Valuation Provider**. Valuations refresh on the schedule set by `RE_VALUATION_REFRESH_SCHEDULE` in `.env` (default: weekly Monday 3am).

### Linking transactions to a property

When adding or editing a transaction, set the **Property** field to associate the transaction with a property. This enables the Property P&L report.

---

## Exports

HearthLedger can export reports as PDF or Excel files.

Go to **Reports**, then click **Export** on any report. Choose a format:

- **PDF** — formatted report suitable for printing or sharing
- **Excel** — raw data in `.xlsx` format for further analysis

**Executor re-authentication:** exports require re-entering your password (a short-lived `reauth_token` is issued and attached to the export request). This prevents an unattended logged-in session from exporting sensitive data.

Export jobs run as background tasks. Watch the **Settings → Exports** page to download completed exports. Export files are retained for 30 days by default.

---

## Backups

HearthLedger automatically backs up your PostgreSQL database.

### Scheduled backups

Backups run on the cron schedule in `BACKUP_SCHEDULE` (default: daily at 2am). Old backups are pruned after `BACKUP_RETENTION_DAYS` days (default: 30).

Backup files are AES-256-GCM encrypted and stored in `./data/backups/` on the host.

### Manual backup

Go to **Settings → Backups** and click **Run backup now**. The page polls every 10 seconds; the status badge updates from `pending` → `processing` → `complete`.

Only the primary household member can trigger or download backups.

### Downloading a backup

Click **Download** next to a completed backup. The file is an encrypted `.dump` archive. To restore:

```bash
# 1. Copy the backup file to the host
# 2. Decrypt it (requires SECRET_ENCRYPTION_KEY from .env)
# 3. Restore with pg_restore:
pg_restore -h localhost -U hearthledger -d hearthledger backup.dump
```

---

## Import History

Go to **Settings → Import History** to see all CSV and OFX import jobs for the household. The table shows the filename, format, status, number of records imported vs. found, and any error message.

---

## Members

HearthLedger supports multiple household members. Each member has a role:

| Role        | Permissions                                                                                                   |
| ----------- | ------------------------------------------------------------------------------------------------------------- |
| `primary`   | Full access — all accounts, all data, backups, exports, member management                                     |
| `partner`   | Own accounts + any accounts explicitly granted; can import and export; cannot manage backups or other members |
| `dependent` | Read-only access to accounts explicitly granted                                                               |

### Adding a member

Go to **Members** in the sidebar and click **New member**. The primary member creates the profile; the new member's login credentials are set at this point.

### Granting account access

See [Access grants](#access-grants-partner-visibility) under Accounts.

---

## Settings

Settings are accessed via the **user menu** in the top-right of the navigation bar. The menu shows your initials (indigo avatar), first name, and a dropdown with:

- Your household name, display name, and role
- Links to Security Log, Activity Log (primary only), Exports, Import History, Backups (primary only), Dashboard Layout, and Appearance
- A **Log out** button that clears your session and returns to the login page

### Appearance

Go to **Settings → Appearance** to choose a color scheme:

- **Light** — always light
- **Dark** — always dark
- **System** — follows your OS preference

The preference is stored locally in your browser.

### Security

Go to **Settings → Security** to change your password. You'll need to enter your current password. Changing your password invalidates all existing refresh tokens (you'll be logged out of other devices).

### Security log

Go to **Settings → Security** and scroll down to the **Login history** section to see your authentication event feed — logins, logouts, failed attempts, and password changes, with timestamps and IP address. Primary members can see all household members' auth events; other roles see only their own.

### Activity log

Go to **Settings → Activity** to see the household audit log — a chronological feed of every data mutation (account created, transaction updated, category renamed, etc.) with timestamps, the actor, and before/after values. The list is filterable by member, entity type, and date range.

The audit log is append-only and cannot be modified or deleted through the application.

Primary members see all household events. Partner and dependent members see events for entities they have access to.

### Per-record history

On any transaction or account detail page, expand the **History** section (collapsible panel at the bottom) to see the full change history for that specific record — who changed what and when, displayed oldest-first as a timeline.
