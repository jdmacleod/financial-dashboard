"""baseline schema

Revision ID: 0001
Revises:
Create Date: 2026-06-16

Creates all 17 tables per docs/data-model.md in dependency order, seeds
system categories under a placeholder household, and locks down audit_log
permissions for the hearthledger_app role.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SYSTEM_HOUSEHOLD_ID = "00000000-0000-0000-0000-000000000000"

INCOME_CATEGORIES = [
    "Salary", "Rental income", "Consulting fees", "Dividends",
    "Interest", "Other income",
]

EXPENSE_CATEGORIES = [
    "Housing", "Utilities", "Groceries", "Dining out", "Transportation",
    "Healthcare", "Insurance", "Personal care", "Entertainment", "Shopping",
    "Education", "Gifts", "Charity", "Travel", "Subscriptions",
    "Business expenses", "Taxes", "Uncategorized", "Transfer",
]


def upgrade() -> None:
    # --- Enums -----------------------------------------------------------
    op.execute(
        "CREATE TYPE member_role AS ENUM ('primary', 'partner', 'dependent')"
    )
    op.execute("CREATE TYPE access_level AS ENUM ('read')")
    op.execute(
        """
        CREATE TYPE account_type AS ENUM (
            'checking', 'savings', 'credit_card',
            'investment_brokerage', 'retirement_401k', 'retirement_403b',
            'retirement_ira', 'retirement_roth_ira',
            'pension', 'hsa',
            'real_estate', 'mortgage',
            'auto_loan', 'personal_loan', 'student_loan',
            'other_asset', 'other_liability'
        )
        """
    )
    op.execute("CREATE TYPE snapshot_source AS ENUM ('manual', 'import')")
    op.execute(
        "CREATE TYPE transaction_source AS ENUM ('manual', 'csv', 'ofx', 'qfx')"
    )
    op.execute(
        "CREATE TYPE valuation_source AS ENUM ('manual', 'api_attom', 'api_estated')"
    )
    op.execute("CREATE TYPE budget_period AS ENUM ('monthly', 'annual')")
    op.execute("CREATE TYPE import_format AS ENUM ('csv', 'ofx', 'qfx')")
    op.execute(
        "CREATE TYPE job_status AS ENUM ('pending', 'processing', 'complete', 'failed')"
    )
    op.execute(
        """
        CREATE TYPE export_type AS ENUM (
            'pdf_summary', 'pdf_executor',
            'excel_summary', 'excel_executor'
        )
        """
    )
    op.execute("CREATE TYPE backup_trigger AS ENUM ('scheduled', 'manual')")

    # --- 1. households -----------------------------------------------------
    op.execute(
        """
        CREATE TABLE households (
            id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name         VARCHAR(120) NOT NULL,
            settings     JSONB NOT NULL DEFAULT '{}',
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # --- 2. household_members ----------------------------------------------
    op.execute(
        """
        CREATE TABLE household_members (
            id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id   UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            display_name   VARCHAR(80) NOT NULL,
            role           member_role NOT NULL DEFAULT 'partner',
            date_of_birth  DATE,
            is_active      BOOLEAN NOT NULL DEFAULT TRUE,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_members_household ON household_members (household_id)"
    )

    # --- 3. users ------------------------------------------------------------
    op.execute(
        """
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
        )
        """
    )

    # --- 4. categories ---------------------------------------------------
    op.execute(
        """
        CREATE TABLE categories (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id       UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            name               VARCHAR(100) NOT NULL,
            parent_category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
            color_hex          CHAR(7) NOT NULL DEFAULT '#888888',
            icon               VARCHAR(50),
            is_income          BOOLEAN NOT NULL DEFAULT FALSE,
            is_system          BOOLEAN NOT NULL DEFAULT FALSE,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (household_id, name)
        )
        """
    )

    # --- 5. accounts -------------------------------------------------------
    op.execute(
        """
        CREATE TABLE accounts (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id           UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            owner_member_id        UUID REFERENCES household_members(id) ON DELETE SET NULL,
            account_type           account_type NOT NULL,
            nickname               VARCHAR(100) NOT NULL,
            institution_name_enc   BYTEA,
            account_number_enc     BYTEA,
            routing_number_enc     BYTEA,
            include_in_net_worth   BOOLEAN NOT NULL DEFAULT TRUE,
            is_active              BOOLEAN NOT NULL DEFAULT TRUE,
            notes_enc              BYTEA,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_accounts_household ON accounts (household_id) WHERE is_active"
    )
    op.execute(
        "CREATE INDEX idx_accounts_owner ON accounts (owner_member_id) WHERE owner_member_id IS NOT NULL"
    )

    # --- 6. account_access_grants -------------------------------------------
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_grants_account ON account_access_grants (account_id) WHERE is_active"
    )
    op.execute(
        "CREATE INDEX idx_grants_grantee ON account_access_grants (grantee_member_id) WHERE is_active"
    )

    # --- 7. account_snapshots -----------------------------------------------
    op.execute(
        """
        CREATE TABLE account_snapshots (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id          UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            snapshot_date       DATE NOT NULL,
            balance             NUMERIC(18,4) NOT NULL,
            contributed_ytd     NUMERIC(18,4),
            employer_match_ytd  NUMERIC(18,4),
            memo                VARCHAR(255),
            source              snapshot_source NOT NULL DEFAULT 'manual',
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (account_id, snapshot_date)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_snapshots_account_date ON account_snapshots (account_id, snapshot_date DESC)"
    )

    # --- 8. real_estate_properties ------------------------------------------
    op.execute(
        """
        CREATE TABLE real_estate_properties (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id                  UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
            address_enc                 BYTEA NOT NULL,
            purchase_date               DATE,
            purchase_price              NUMERIC(18,4),
            linked_mortgage_account_id  UUID REFERENCES accounts(id) ON DELETE SET NULL,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # --- 9. property_valuations ----------------------------------------------
    op.execute(
        """
        CREATE TABLE property_valuations (
            id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            real_estate_property_id   UUID NOT NULL REFERENCES real_estate_properties(id) ON DELETE CASCADE,
            valuation_date            DATE NOT NULL,
            estimated_value           NUMERIC(18,4) NOT NULL,
            source                    valuation_source NOT NULL DEFAULT 'manual',
            confidence_score          NUMERIC(4,3),
            raw_response              JSONB,
            created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_valuations_property_date ON property_valuations (real_estate_property_id, valuation_date DESC)"
    )

    # --- 10. debts -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE debts (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id        UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
            original_balance  NUMERIC(18,4) NOT NULL,
            current_balance   NUMERIC(18,4) NOT NULL,
            interest_rate     NUMERIC(6,4) NOT NULL,
            minimum_payment   NUMERIC(12,2) NOT NULL,
            payment_due_day   SMALLINT,
            loan_term_months  INTEGER,
            origination_date  DATE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    # --- 11. transactions ------------------------------------------------
    op.execute(
        """
        CREATE TABLE transactions (
            id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id                UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            real_estate_property_id   UUID REFERENCES real_estate_properties(id) ON DELETE SET NULL,
            transaction_date          DATE NOT NULL,
            post_date                 DATE,
            amount                    NUMERIC(18,4) NOT NULL,
            payee_raw                 VARCHAR(255),
            payee_normalized          VARCHAR(255),
            memo                      VARCHAR(500),
            category_id               UUID REFERENCES categories(id) ON DELETE SET NULL,
            is_transfer               BOOLEAN NOT NULL DEFAULT FALSE,
            transfer_pair_id          UUID,
            tags                      TEXT[] NOT NULL DEFAULT '{}',
            source                    transaction_source NOT NULL DEFAULT 'manual',
            import_job_id             UUID,
            external_id               VARCHAR(255),
            is_reviewed               BOOLEAN NOT NULL DEFAULT FALSE,
            created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_txn_account_date ON transactions (account_id, transaction_date DESC)"
    )
    op.execute("CREATE INDEX idx_txn_category ON transactions (category_id)")
    op.execute(
        "CREATE INDEX idx_txn_property ON transactions (real_estate_property_id) WHERE real_estate_property_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_txn_external ON transactions (account_id, external_id) WHERE external_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_txn_import_job ON transactions (import_job_id) WHERE import_job_id IS NOT NULL"
    )

    # --- 12. budgets -----------------------------------------------------
    op.execute(
        """
        CREATE TABLE budgets (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            category_id     UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            period          budget_period NOT NULL DEFAULT 'monthly',
            amount          NUMERIC(12,2) NOT NULL,
            effective_from  DATE NOT NULL,
            effective_to    DATE,

            CONSTRAINT no_negative_budget CHECK (amount >= 0)
        )
        """
    )
    op.execute("CREATE INDEX idx_budgets_household ON budgets (household_id)")
    op.execute("CREATE INDEX idx_budgets_category ON budgets (category_id)")

    # --- 13. fire_scenarios ------------------------------------------------
    op.execute(
        """
        CREATE TABLE fire_scenarios (
            id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id                UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            name                        VARCHAR(100) NOT NULL,
            target_annual_spend         NUMERIC(12,2) NOT NULL,
            safe_withdrawal_rate        NUMERIC(5,4) NOT NULL DEFAULT 0.04,
            expected_annual_return      NUMERIC(5,4) NOT NULL DEFAULT 0.07,
            expected_inflation_rate     NUMERIC(5,4) NOT NULL DEFAULT 0.03,
            target_retirement_age       SMALLINT,
            additional_income_streams   JSONB NOT NULL DEFAULT '[]',
            detected_annual_income      NUMERIC(12,2),
            detected_annual_expenses    NUMERIC(12,2),
            detected_savings_rate       NUMERIC(5,4),
            detected_portfolio_value    NUMERIC(18,4),
            detection_trailing_months   SMALLINT NOT NULL DEFAULT 12,
            detected_at                 TIMESTAMPTZ,
            created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_fire_household ON fire_scenarios (household_id)")

    # --- 14. import_jobs -----------------------------------------------------
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        "ALTER TABLE transactions ADD CONSTRAINT fk_txn_import_job "
        "FOREIGN KEY (import_job_id) REFERENCES import_jobs(id) ON DELETE SET NULL"
    )

    # --- 15. export_jobs -------------------------------------------------
    op.execute(
        """
        CREATE TABLE export_jobs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id    UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            export_type     export_type NOT NULL,
            anonymized      BOOLEAN NOT NULL,
            parameters      JSONB NOT NULL DEFAULT '{}',
            status          job_status NOT NULL DEFAULT 'pending',
            filename        VARCHAR(255),
            error_message   TEXT,
            generated_by    UUID NOT NULL REFERENCES users(id),
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at    TIMESTAMPTZ
        )
        """
    )

    # --- 16. backup_jobs -------------------------------------------------
    op.execute(
        """
        CREATE TABLE backup_jobs (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            triggered_by         backup_trigger NOT NULL DEFAULT 'scheduled',
            triggered_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            status               job_status NOT NULL DEFAULT 'processing',
            filename             VARCHAR(255),
            file_size_bytes      BIGINT,
            error_message        TEXT,
            started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at         TIMESTAMPTZ
        )
        """
    )

    # --- 17. audit_log -----------------------------------------------------
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_audit_household_created ON audit_log (household_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_user ON audit_log (user_id, created_at DESC)"
    )

    # --- hearthledger_app permissions ---------------------------------------
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO hearthledger_app")
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hearthledger_app"
    )
    op.execute("REVOKE ALL ON audit_log FROM hearthledger_app")
    op.execute("GRANT SELECT, INSERT ON audit_log TO hearthledger_app")

    # --- Seed system categories ---------------------------------------------
    op.execute(
        f"""
        INSERT INTO households (id, name, settings)
        VALUES ('{SYSTEM_HOUSEHOLD_ID}', 'SYSTEM_TEMPLATE', '{{}}')
        """
    )
    for name in INCOME_CATEGORIES:
        op.execute(
            f"""
            INSERT INTO categories (household_id, name, is_income, is_system)
            VALUES ('{SYSTEM_HOUSEHOLD_ID}', '{name}', TRUE, TRUE)
            """
        )
    for name in EXPENSE_CATEGORIES:
        op.execute(
            f"""
            INSERT INTO categories (household_id, name, is_income, is_system)
            VALUES ('{SYSTEM_HOUSEHOLD_ID}', '{name}', FALSE, TRUE)
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log")
    op.execute("DROP TABLE IF EXISTS backup_jobs")
    op.execute("DROP TABLE IF EXISTS export_jobs")
    op.execute("ALTER TABLE IF EXISTS transactions DROP CONSTRAINT IF EXISTS fk_txn_import_job")
    op.execute("DROP TABLE IF EXISTS import_jobs")
    op.execute("DROP TABLE IF EXISTS fire_scenarios")
    op.execute("DROP TABLE IF EXISTS budgets")
    op.execute("DROP TABLE IF EXISTS transactions")
    op.execute("DROP TABLE IF EXISTS debts")
    op.execute("DROP TABLE IF EXISTS property_valuations")
    op.execute("DROP TABLE IF EXISTS real_estate_properties")
    op.execute("DROP TABLE IF EXISTS account_snapshots")
    op.execute("DROP TABLE IF EXISTS account_access_grants")
    op.execute("DROP TABLE IF EXISTS accounts")
    op.execute("DROP TABLE IF EXISTS categories")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TABLE IF EXISTS household_members")
    op.execute("DROP TABLE IF EXISTS households")

    op.execute("DROP TYPE IF EXISTS backup_trigger")
    op.execute("DROP TYPE IF EXISTS export_type")
    op.execute("DROP TYPE IF EXISTS job_status")
    op.execute("DROP TYPE IF EXISTS import_format")
    op.execute("DROP TYPE IF EXISTS budget_period")
    op.execute("DROP TYPE IF EXISTS valuation_source")
    op.execute("DROP TYPE IF EXISTS transaction_source")
    op.execute("DROP TYPE IF EXISTS snapshot_source")
    op.execute("DROP TYPE IF EXISTS account_type")
    op.execute("DROP TYPE IF EXISTS access_level")
    op.execute("DROP TYPE IF EXISTS member_role")
