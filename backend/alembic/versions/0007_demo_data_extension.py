"""Demo-data extension: ownership entities, insurance, equity comp, lots,
capital commitments, advisory notes; account_type enum + column additions.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-22

Phase A of the demo-data revision spec. Adds the seven structural tables the
existing dataset cannot express, extends account_type with five (six incl.
inherited_ira) new values, and adds the ownership-entity titling FK plus the
is_revolving flag to accounts. New tables get standard app-role DML grants;
audit_log is left untouched at SELECT/INSERT only (CLAUDE.md rule #3).

Note on reversibility: PostgreSQL cannot DROP enum values, so the downgrade
reclassifies any accounts using the new account_type values to other_asset/
other_liability, then recreates the enum without them (same dance as 0005).
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_NEW_TABLES = (
    "ownership_entity",
    "investment_lot",
    "equity_grant",
    "vesting_event",
    "insurance_policy",
    "capital_commitment",
    "advisory_note",
)


def upgrade() -> None:
    # --- New enums --------------------------------------------------------
    op.execute(
        """
        CREATE TYPE ownership_entity_type AS ENUM (
            'revocable_trust', 'irrevocable_trust', 'ilit',
            'crt_crat', 'crt_crut', 'clt', 'llc',
            'custodial_utma', 'custodial_ugma'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE insurance_policy_type AS ENUM (
            'term_life', 'permanent_life', 'umbrella_liability',
            'disability', 'long_term_care', 'scheduled_specialty'
        )
        """
    )
    op.execute("CREATE TYPE premium_cadence AS ENUM ('monthly', 'quarterly', 'annual')")
    op.execute("CREATE TYPE equity_grant_type AS ENUM ('rsu', 'iso', 'nso', 'espp')")
    op.execute(
        """
        CREATE TYPE lot_basis_type AS ENUM (
            'purchase', 'rsu_vest', 'espp', 'inherited_stepup',
            'gift_carryover', 'reinvested_dividend'
        )
        """
    )
    op.execute(
        """
        CREATE TYPE advisory_note_category AS ENUM (
            'estate', 'tax', 'concentration', 'insurance',
            'retirement', 'charitable', 'scope_omission'
        )
        """
    )

    # --- Extend account_type ---------------------------------------------
    # ALTER TYPE ... ADD VALUE commits immediately in PG12+ even inside a txn;
    # the new values are not used by any statement in this migration, so the
    # same-transaction-usage restriction does not apply here.
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'inherited_ira'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'sbloc'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'margin'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'private_fund'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'life_insurance_cash_value'")
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'treasury'")

    # --- ownership_entity (must precede the titling FKs) ------------------
    op.execute(
        """
        CREATE TABLE ownership_entity (
            id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id                  UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            entity_type                   ownership_entity_type NOT NULL,
            name_enc                      BYTEA NOT NULL,
            grantor_member_id             UUID REFERENCES household_members(id) ON DELETE SET NULL,
            is_in_taxable_estate          BOOLEAN NOT NULL DEFAULT TRUE,
            counts_in_personal_net_worth  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_ownership_entity_household ON ownership_entity (household_id)"
    )

    # --- Titling FKs + revolving flag on existing tables ------------------
    op.execute(
        """
        ALTER TABLE accounts
            ADD COLUMN ownership_entity_id UUID
                REFERENCES ownership_entity(id) ON DELETE SET NULL,
            ADD COLUMN is_revolving BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        "CREATE INDEX idx_accounts_ownership_entity ON accounts (ownership_entity_id) "
        "WHERE ownership_entity_id IS NOT NULL"
    )
    op.execute(
        """
        ALTER TABLE real_estate_properties
            ADD COLUMN ownership_entity_id UUID
                REFERENCES ownership_entity(id) ON DELETE SET NULL
        """
    )

    # --- investment_lot (referenced by vesting_event) ---------------------
    op.execute(
        """
        CREATE TABLE investment_lot (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id       UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            ticker           VARCHAR(16) NOT NULL,
            shares           NUMERIC(18,6) NOT NULL,
            basis_per_share  NUMERIC(18,6) NOT NULL,
            acquired_date    DATE NOT NULL,
            basis_type       lot_basis_type NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_investment_lot_account ON investment_lot (account_id)")

    # --- equity_grant + vesting_event -------------------------------------
    op.execute(
        """
        CREATE TABLE equity_grant (
            id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id       UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            member_id          UUID NOT NULL REFERENCES household_members(id) ON DELETE CASCADE,
            grant_type         equity_grant_type NOT NULL,
            grant_date         DATE NOT NULL,
            shares_granted     NUMERIC(18,6) NOT NULL,
            strike_price       NUMERIC(18,4),
            ticker             VARCHAR(16) NOT NULL,
            vesting_schedule   JSONB NOT NULL DEFAULT '{}',
            espp_discount_pct  NUMERIC(5,4),
            espp_lookback      BOOLEAN,
            created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_equity_grant_household ON equity_grant (household_id)")
    op.execute(
        """
        CREATE TABLE vesting_event (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            equity_grant_id          UUID NOT NULL REFERENCES equity_grant(id) ON DELETE CASCADE,
            event_date               DATE NOT NULL,
            shares_vested            NUMERIC(18,6) NOT NULL,
            fmv_at_event             NUMERIC(18,4) NOT NULL,
            taxable_ordinary_income  NUMERIC(18,4) NOT NULL,
            amt_preference_amount    NUMERIC(18,4),
            shares_sold_to_cover     NUMERIC(18,6) NOT NULL DEFAULT 0,
            resulting_lot_id         UUID REFERENCES investment_lot(id) ON DELETE SET NULL,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_vesting_event_grant ON vesting_event (equity_grant_id)")

    # --- insurance_policy -------------------------------------------------
    op.execute(
        """
        CREATE TABLE insurance_policy (
            id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id               UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            policy_type                insurance_policy_type NOT NULL,
            insured_member_id          UUID REFERENCES household_members(id) ON DELETE SET NULL,
            owner_ownership_entity_id  UUID REFERENCES ownership_entity(id) ON DELETE SET NULL,
            coverage_amount            NUMERIC(18,4) NOT NULL,
            premium_amount             NUMERIC(18,4) NOT NULL,
            premium_cadence            premium_cadence NOT NULL,
            cash_value_account_id      UUID REFERENCES accounts(id) ON DELETE SET NULL,
            metadata                   JSONB NOT NULL DEFAULT '{}',
            created_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_insurance_policy_household ON insurance_policy (household_id)")

    # --- capital_commitment -----------------------------------------------
    op.execute(
        """
        CREATE TABLE capital_commitment (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id      UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            fund_name_enc     BYTEA NOT NULL,
            committed_amount  NUMERIC(18,4) NOT NULL,
            called_to_date    NUMERIC(18,4) NOT NULL DEFAULT 0,
            nav_account_id    UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            vintage_year      INTEGER NOT NULL,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_capital_commitment_household ON capital_commitment (household_id)"
    )

    # --- advisory_note ----------------------------------------------------
    op.execute(
        """
        CREATE TABLE advisory_note (
            id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            household_id         UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
            account_id           UUID REFERENCES accounts(id) ON DELETE SET NULL,
            ownership_entity_id  UUID REFERENCES ownership_entity(id) ON DELETE SET NULL,
            category             advisory_note_category NOT NULL,
            title                VARCHAR(200) NOT NULL,
            body                 TEXT NOT NULL,
            created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_advisory_note_household ON advisory_note (household_id)")

    # --- hearthledger_app grants (audit_log untouched, rule #3) -----------
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON "
        + ", ".join(_NEW_TABLES)
        + " TO hearthledger_app"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS advisory_note")
    op.execute("DROP TABLE IF EXISTS capital_commitment")
    op.execute("DROP TABLE IF EXISTS insurance_policy")
    op.execute("DROP TABLE IF EXISTS vesting_event")
    op.execute("DROP TABLE IF EXISTS equity_grant")
    op.execute("DROP TABLE IF EXISTS investment_lot")

    op.execute("DROP INDEX IF EXISTS idx_accounts_ownership_entity")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS ownership_entity_id")
    op.execute("ALTER TABLE accounts DROP COLUMN IF EXISTS is_revolving")
    op.execute(
        "ALTER TABLE real_estate_properties DROP COLUMN IF EXISTS ownership_entity_id"
    )
    op.execute("DROP TABLE IF EXISTS ownership_entity")

    op.execute("DROP TYPE IF EXISTS advisory_note_category")
    op.execute("DROP TYPE IF EXISTS lot_basis_type")
    op.execute("DROP TYPE IF EXISTS equity_grant_type")
    op.execute("DROP TYPE IF EXISTS premium_cadence")
    op.execute("DROP TYPE IF EXISTS insurance_policy_type")
    op.execute("DROP TYPE IF EXISTS ownership_entity_type")

    # PostgreSQL cannot remove enum values; recreate account_type without the
    # new ones. Reclassify any accounts using them first so the USING cast
    # does not fail on values absent from the rebuilt enum.
    op.execute(
        "UPDATE accounts SET account_type = 'other_asset' WHERE account_type IN "
        "('inherited_ira', 'private_fund', 'life_insurance_cash_value', 'treasury')"
    )
    op.execute(
        "UPDATE accounts SET account_type = 'other_liability' WHERE account_type IN "
        "('sbloc', 'margin')"
    )
    op.execute("ALTER TABLE accounts ALTER COLUMN account_type TYPE TEXT")
    op.execute("DROP TYPE account_type")
    op.execute(
        """
        CREATE TYPE account_type AS ENUM (
            'checking', 'savings', 'credit_card',
            'investment_brokerage',
            'retirement_401k', 'retirement_403b', 'retirement_ira', 'retirement_roth_ira',
            'pension', 'hsa',
            'real_estate', 'mortgage', 'auto_loan', 'personal_loan', 'heloc', 'student_loan',
            'other_asset', 'other_liability'
        )
        """
    )
    op.execute(
        "ALTER TABLE accounts ALTER COLUMN account_type TYPE account_type "
        "USING account_type::account_type"
    )
