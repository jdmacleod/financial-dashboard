"""Create pension_accounts table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-18
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE pension_accounts (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id               UUID NOT NULL UNIQUE REFERENCES accounts(id) ON DELETE CASCADE,
            member_id                UUID REFERENCES household_members(id) ON DELETE SET NULL,
            plan_name_enc            BYTEA,
            administrator_enc        BYTEA,
            monthly_benefit_estimate NUMERIC(18, 4),
            eligibility_age          SMALLINT,
            eligibility_date         DATE,
            cola_adjustment_rate     NUMERIC(5, 4) NOT NULL DEFAULT 0.02,
            is_vested                BOOLEAN NOT NULL DEFAULT FALSE,
            vesting_date             DATE,
            survivor_benefit_percent NUMERIC(5, 4),
            notes_enc                BYTEA,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON pension_accounts TO hearthledger_app")


def downgrade() -> None:
    op.execute("DROP TABLE pension_accounts")
