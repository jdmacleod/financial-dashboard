# Data Model

Consolidated schema incorporating all design amendments (1–3).
All tables use UUID primary keys. All timestamps are TIMESTAMPTZ.
All monetary values are NUMERIC(18,4). Currency is USD only (v1).

---

## households

```sql
CREATE TABLE households (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         VARCHAR(120) NOT NULL,
    settings     JSONB NOT NULL DEFAULT '{}',
    -- settings keys: fiscal_year_start_month (int, default 1)
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

One row per installation. `settings` is reserved for future locale/fiscal-year config.

---

## household_members

```sql
CREATE TYPE member_role AS ENUM ('primary', 'partner', 'dependent');

CREATE TABLE household_members (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id   UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    display_name   VARCHAR(80) NOT NULL,
    role           member_role NOT NULL DEFAULT 'partner',
    date_of_birth  DATE,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_members_household ON household_members (household_id);
```

---

## users

```sql
CREATE TABLE users (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id              UUID REFERENCES household_members(id) ON DELETE SET NULL,
    email                  VARCHAR(255) NOT NULL UNIQUE,
    hashed_password        VARCHAR NOT NULL,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    refresh_token_hash     VARCHAR,
    failed_login_attempts  SMALLINT NOT NULL DEFAULT 0,
    locked_until           TIMESTAMPTZ,
    last_password_change   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login             TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## account_access_grants

```sql
CREATE TYPE access_level AS ENUM ('read');

CREATE TABLE account_access_grants (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id           UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    owner_member_id      UUID NOT NULL REFERENCES household_members(id),
    grantee_member_id    UUID NOT NULL REFERENCES household_members(id),
    granted_by_user_id   UUID NOT NULL REFERENCES users(id),
    access_level         access_level NOT NULL DEFAULT 'read',
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at           TIMESTAMPTZ,

    CONSTRAINT different_members CHECK (owner_member_id != grantee_member_id)
);

CREATE INDEX idx_grants_account    ON account_access_grants (account_id) WHERE is_active;
CREATE INDEX idx_grants_grantee    ON account_access_grants (grantee_member_id) WHERE is_active;
```

---

## accounts

```sql
CREATE TYPE account_type AS ENUM (
    'checking', 'savings', 'credit_card',
    'investment_brokerage', 'retirement_401k', 'retirement_403b',
    'retirement_ira', 'retirement_roth_ira',
    'pension', 'hsa',
    'real_estate', 'mortgage',
    'auto_loan', 'personal_loan', 'student_loan',
    'other_asset', 'other_liability'
);

CREATE TABLE accounts (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id           UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    owner_member_id        UUID REFERENCES household_members(id) ON DELETE SET NULL,
    -- NULL owner_member_id = joint account
    account_type           account_type NOT NULL,
    nickname               VARCHAR(100) NOT NULL,
    institution_name_enc   BYTEA,        -- AES-256-GCM encrypted
    account_number_enc     BYTEA,        -- AES-256-GCM encrypted
    routing_number_enc     BYTEA,        -- AES-256-GCM encrypted; optional
    include_in_net_worth   BOOLEAN NOT NULL DEFAULT TRUE,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    notes_enc              BYTEA,        -- AES-256-GCM encrypted; optional
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_accounts_household ON accounts (household_id) WHERE is_active;
CREATE INDEX idx_accounts_owner     ON accounts (owner_member_id) WHERE owner_member_id IS NOT NULL;
```

### Visibility rule (implemented in AccountRepository)

```
account visible to user when:
  account.owner_member_id IS NULL                              -- joint
  OR account.owner_member_id = user.member_id                  -- own
  OR user.member.role = 'primary'                              -- admin
  OR EXISTS (SELECT 1 FROM account_access_grants
             WHERE account_id = account.id
             AND grantee_member_id = user.member_id
             AND is_active = TRUE)                             -- granted
```

---

## account_snapshots

Point-in-time balance records. Used for all account types that don't
have individual transactions (investment, retirement, pension, HSA, real
estate, mortgage balance). Checking/savings/credit cards may also have
snapshots for reconciliation.

```sql
CREATE TYPE snapshot_source AS ENUM ('manual', 'import');

CREATE TABLE account_snapshots (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id          UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    snapshot_date       DATE NOT NULL,
    balance             NUMERIC(18,4) NOT NULL,
    contributed_ytd     NUMERIC(18,4),   -- for 401k, IRA, HSA
    employer_match_ytd  NUMERIC(18,4),   -- for 401k, 403b
    memo                VARCHAR(255),
    source              snapshot_source NOT NULL DEFAULT 'manual',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (account_id, snapshot_date)   -- one snapshot per account per day
);

CREATE INDEX idx_snapshots_account_date ON account_snapshots (account_id, snapshot_date DESC);
```

---

## categories

```sql
CREATE TABLE categories (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id       UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name               VARCHAR(100) NOT NULL,
    parent_category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    color_hex          CHAR(7) NOT NULL DEFAULT '#888888',
    icon               VARCHAR(50),
    is_income          BOOLEAN NOT NULL DEFAULT FALSE,
    is_system          BOOLEAN NOT NULL DEFAULT FALSE, -- seeded defaults; non-deletable
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (household_id, name)
);
```

### Seeded system categories (created in baseline migration)

Income: Salary, Rental income, Consulting fees, Dividends, Interest, Other income

Expenses: Housing, Utilities, Groceries, Dining out, Transportation, Healthcare,
Insurance, Personal care, Entertainment, Shopping, Education, Gifts, Charity,
Travel, Subscriptions, Business expenses, Taxes, Uncategorized

---

## transactions

```sql
CREATE TYPE transaction_source AS ENUM ('manual', 'csv', 'ofx', 'qfx');

CREATE TABLE transactions (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id                UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    real_estate_property_id   UUID REFERENCES real_estate_properties(id) ON DELETE SET NULL,
    -- Amendment 3: optional property tag for rental income / property expenses
    transaction_date          DATE NOT NULL,
    post_date                 DATE,
    amount                    NUMERIC(18,4) NOT NULL,
    -- positive = credit (money in), negative = debit (money out)
    payee_raw                 VARCHAR(255),
    payee_normalized          VARCHAR(255),
    memo                      VARCHAR(500),
    category_id               UUID REFERENCES categories(id) ON DELETE SET NULL,
    is_transfer               BOOLEAN NOT NULL DEFAULT FALSE,
    transfer_pair_id          UUID,        -- links both sides of a transfer
    tags                      TEXT[] NOT NULL DEFAULT '{}',
    source                    transaction_source NOT NULL DEFAULT 'manual',
    import_job_id             UUID REFERENCES import_jobs(id) ON DELETE SET NULL,
    external_id               VARCHAR(255), -- bank's ID; used for dedup
    is_reviewed               BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_txn_account_date     ON transactions (account_id, transaction_date DESC);
CREATE INDEX idx_txn_category         ON transactions (category_id);
CREATE INDEX idx_txn_property         ON transactions (real_estate_property_id)
                                       WHERE real_estate_property_id IS NOT NULL;
CREATE INDEX idx_txn_external         ON transactions (account_id, external_id)
                                       WHERE external_id IS NOT NULL;
CREATE INDEX idx_txn_import_job       ON transactions (import_job_id)
                                       WHERE import_job_id IS NOT NULL;
```

---

## real_estate_properties

Companion table to an account of type `real_estate`.

```sql
CREATE TABLE real_estate_properties (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id                  UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
    address_enc                 BYTEA NOT NULL,   -- AES-256-GCM encrypted
    purchase_date               DATE,
    purchase_price              NUMERIC(18,4),
    linked_mortgage_account_id  UUID REFERENCES accounts(id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Current estimated value is stored in `property_valuations` (most recent row),
not as a column on this table.

---

## property_valuations

Valuation history from API providers and manual entry.

```sql
CREATE TYPE valuation_source AS ENUM ('manual', 'api_attom', 'api_estated');

CREATE TABLE property_valuations (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    real_estate_property_id   UUID NOT NULL REFERENCES real_estate_properties(id) ON DELETE CASCADE,
    valuation_date            DATE NOT NULL,
    estimated_value           NUMERIC(18,4) NOT NULL,
    source                    valuation_source NOT NULL DEFAULT 'manual',
    confidence_score          NUMERIC(4,3),   -- 0.000–1.000; NULL if provider doesn't supply
    raw_response              JSONB,          -- provider response for audit; nullable
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_valuations_property_date
    ON property_valuations (real_estate_property_id, valuation_date DESC);
```

To get current value: `SELECT estimated_value FROM property_valuations
WHERE real_estate_property_id = $1 ORDER BY valuation_date DESC LIMIT 1`

---

## debts

Companion table to mortgage/loan accounts for payoff projection.

```sql
CREATE TABLE debts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id        UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
    original_balance  NUMERIC(18,4) NOT NULL,
    current_balance   NUMERIC(18,4) NOT NULL,
    interest_rate     NUMERIC(6,4) NOT NULL,   -- e.g. 0.0675 for 6.75%
    minimum_payment   NUMERIC(12,2) NOT NULL,
    payment_due_day   SMALLINT,                -- day of month
    loan_term_months  INTEGER,
    origination_date  DATE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## budgets

```sql
CREATE TYPE budget_period AS ENUM ('monthly', 'annual');

CREATE TABLE budgets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    category_id     UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    period          budget_period NOT NULL DEFAULT 'monthly',
    amount          NUMERIC(12,2) NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,   -- NULL = ongoing

    CONSTRAINT no_negative_budget CHECK (amount >= 0)
);

CREATE INDEX idx_budgets_household   ON budgets (household_id);
CREATE INDEX idx_budgets_category    ON budgets (category_id);
```

---

## fire_scenarios

```sql
CREATE TABLE fire_scenarios (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id                UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    name                        VARCHAR(100) NOT NULL,
    target_annual_spend         NUMERIC(12,2) NOT NULL,
    safe_withdrawal_rate        NUMERIC(5,4) NOT NULL DEFAULT 0.04,
    expected_annual_return      NUMERIC(5,4) NOT NULL DEFAULT 0.07,
    expected_inflation_rate     NUMERIC(5,4) NOT NULL DEFAULT 0.03,
    target_retirement_age       SMALLINT,

    -- Income streams (Amendment 3) — see IncomeStream schema in docs/phase-4-fire-and-debt.md
    additional_income_streams   JSONB NOT NULL DEFAULT '[]',

    -- Auto-detected values (Amendment 1 + 3)
    detected_annual_income      NUMERIC(12,2),
    detected_annual_expenses    NUMERIC(12,2),
    detected_savings_rate       NUMERIC(5,4),
    detected_portfolio_value    NUMERIC(18,4),
    detection_trailing_months   SMALLINT NOT NULL DEFAULT 12,
    detected_at                 TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_fire_household ON fire_scenarios (household_id);
```

---

## import_jobs

```sql
CREATE TYPE import_format AS ENUM ('csv', 'ofx', 'qfx');
CREATE TYPE job_status    AS ENUM ('pending', 'processing', 'complete', 'failed');

CREATE TABLE import_jobs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id        UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    filename          VARCHAR(255) NOT NULL,
    format            import_format NOT NULL,
    status            job_status NOT NULL DEFAULT 'pending',
    records_found     INTEGER,
    records_imported  INTEGER,
    records_skipped   INTEGER,
    error_message     TEXT,
    imported_by       UUID NOT NULL REFERENCES users(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## export_jobs

```sql
CREATE TYPE export_type AS ENUM (
    'pdf_summary', 'pdf_executor',
    'excel_summary', 'excel_executor'
);

CREATE TABLE export_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    export_type     export_type NOT NULL,
    anonymized      BOOLEAN NOT NULL,
    parameters      JSONB NOT NULL DEFAULT '{}',
    -- parameters keys: from_date, to_date, account_ids (list), include_transactions (bool)
    status          job_status NOT NULL DEFAULT 'pending',
    filename        VARCHAR(255),
    error_message   TEXT,
    generated_by    UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ
);
```

---

## backup_jobs

```sql
CREATE TYPE backup_trigger AS ENUM ('scheduled', 'manual');

CREATE TABLE backup_jobs (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_by         backup_trigger NOT NULL DEFAULT 'scheduled',
    triggered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    status               job_status NOT NULL DEFAULT 'running',
    filename             VARCHAR(255),
    file_size_bytes      BIGINT,
    error_message        TEXT,
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);
```

---

## audit_log

Append-only. The `hearthledger_app` Postgres role has SELECT and INSERT only.

```sql
CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(60) NOT NULL,
    entity_type     VARCHAR(40) NOT NULL,
    entity_id       UUID,
    previous_value  JSONB,
    new_value       JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_household_created ON audit_log (household_id, created_at DESC);
CREATE INDEX idx_audit_entity            ON audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_user              ON audit_log (user_id, created_at DESC);
```

### DB role permissions (set in baseline migration)

```sql
-- Applied after tables are created
REVOKE ALL ON audit_log FROM hearthledger_app;
GRANT SELECT, INSERT ON audit_log TO hearthledger_app;
```

### Audit event catalog

| action | entity_type | notes |
|---|---|---|
| auth.login_success | auth | ip_address captured |
| auth.login_failed | auth | ip_address; entity_id null |
| auth.logout | auth | |
| auth.account_locked | auth | new_value: {failed_attempt_count} |
| auth.password_changed | auth | |
| auth.executor_reauth_success | auth | |
| member.created | member | new_value: {display_name, role} |
| member.role_changed | member | prev/new: {role} |
| member.deactivated | member | |
| member.reactivated | member | |
| member.access_grant_created | member | new_value: {account_id, grantee_member_id} |
| member.access_grant_revoked | member | prev: {account_id, grantee_member_id} |
| account.created | account | new_value: {nickname, account_type, owner_member_id} |
| account.updated | account | prev/new: changed fields only; never encrypted fields |
| account.deactivated | account | |
| account.reactivated | account | |
| transaction.created | transaction | new_value: {amount, payee_normalized, transaction_date, category_id} |
| transaction.category_changed | transaction | prev/new: {category_id} |
| transaction.amount_changed | transaction | prev/new: {amount} |
| transaction.payee_changed | transaction | prev/new: {payee_normalized} |
| transaction.transfer_flagged | transaction | new_value: {is_transfer, transfer_pair_id} |
| transaction.property_tagged | transaction | prev/new: {real_estate_property_id} |
| transaction.deleted | transaction | prev: {amount, payee_normalized, transaction_date} |
| snapshot.created | snapshot | new_value: {balance, snapshot_date, source} |
| snapshot.updated | snapshot | prev/new: {balance} |
| snapshot.deleted | snapshot | prev: {balance, snapshot_date} |
| budget.created | budget | new_value: {category_id, period, amount} |
| budget.updated | budget | changed fields only |
| budget.deleted | budget | prev: {category_id, period, amount} |
| category.created | category | new_value: {name, is_income} |
| category.updated | category | changed fields only |
| category.deleted | category | prev: {name} |
| fire_scenario.created | fire_scenario | new_value: {name} |
| fire_scenario.updated | fire_scenario | changed fields only |
| fire_scenario.detection_run | fire_scenario | new_value: {detected_annual_income, detected_at} |
| import.completed | import_job | new_value: {records_imported, filename} |
| import.failed | import_job | |
| export.generated | export_job | new_value: {export_type, anonymized} |
| backup.completed | backup_job | new_value: {filename, file_size_bytes} |
| backup.failed | backup_job | |

---

## Entity-relationship summary

```
households
  ├── household_members (role: primary | partner | dependent)
  │     └── users (login credentials)
  ├── accounts (owner_member_id NULL = joint)
  │     ├── account_snapshots
  │     ├── transactions
  │     │     └── [real_estate_property_id → real_estate_properties]
  │     ├── real_estate_properties
  │     │     └── property_valuations
  │     ├── debts
  │     └── import_jobs
  ├── categories (hierarchical)
  ├── budgets → categories
  ├── fire_scenarios
  ├── export_jobs
  ├── backup_jobs
  └── audit_log
account_access_grants (owner_member → grantee_member, for specific account)
```
