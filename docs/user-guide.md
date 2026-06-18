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
| `retirement` | 401k, IRA, Roth IRA |
| `loan` | Mortgage, car loan, student loan |

**Access grants (partner visibility):**
By default, partner members can only see accounts they own. The primary member can grant read access to an account: go to the account detail page and click **Manage access** to add or remove grants.

**Balances for investment/retirement accounts:**
Rather than individual holdings, HearthLedger uses balance snapshots. Go to the account's **Snapshots** tab and record a balance as of a date. The net worth calculation uses the most recent snapshot.

**Deactivating an account:**
Click the **…** menu on an account and choose **Deactivate**. Deactivated accounts are hidden from lists but historical data is preserved.

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

FIRE (Financial Independence, Retire Early) scenarios let you model retirement timelines based on your current financial position.

### Creating a scenario

Go to **FIRE** in the sidebar and click **New scenario**. Fill in:

- **Name** — e.g. "Coast FIRE at 45"
- **Target year** — when you want to retire
- **Annual expenses** — estimated annual spending in retirement (today's dollars)
- **Safe withdrawal rate** — typically 4.0%
- **Income streams** — salary, rental income, Social Security, etc. Each stream has a name, annual amount, start year, and end year

### Auto-detect

Click **Detect from history** to have HearthLedger calculate your trailing average income and expenses from actual transactions. The trailing window defaults to 12 months (configurable 1–60 months).

### Projection

After saving a scenario, click **Projection** to see a year-by-year chart of portfolio value vs. the FIRE target. The projection uses compound growth on your current net worth and shows the projected retirement year.

---

## Debt Payoff

Go to **Debt** in the sidebar to see a payoff analysis of all your loan and credit accounts.

The analysis shows:

- Current balance and interest rate for each debt
- Minimum monthly payment
- Payoff date under the current plan
- How much faster you'd pay off with an extra monthly payment

Set the **extra monthly payment** slider to model accelerated payoff. Two strategies are available:

- **Avalanche** — pay highest-interest debt first (minimizes total interest)
- **Snowball** — pay smallest balance first (psychological wins)

---

## Real Estate

Real estate properties are tracked under **Properties** in the sidebar.

### Adding a property

Click **New property** and enter:

- Address (stored encrypted)
- Purchase date and price
- Current estimated value (or use a valuation provider — see below)

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
