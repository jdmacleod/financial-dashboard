"""Create pension_estimate_history and backfill from current estimates.

Net-worth points are now valued from the pension estimate in effect at each
date, so editing a benefit estimate no longer rewrites historical chart points.
Existing pensions are backfilled with a single row (effective from creation)
carrying their current present-value inputs.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-22
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE pension_estimate_history (
            id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pension_account_id       UUID NOT NULL REFERENCES pension_accounts(id) ON DELETE CASCADE,
            effective_date           DATE NOT NULL,
            monthly_benefit_estimate NUMERIC(18, 4),
            cola_adjustment_rate     NUMERIC(5, 4) NOT NULL DEFAULT 0.02,
            survivor_benefit_percent NUMERIC(5, 4),
            eligibility_date         DATE,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (pension_account_id, effective_date)
        )
    """)
    op.execute(
        "CREATE INDEX idx_pension_estimate_history_account "
        "ON pension_estimate_history (pension_account_id, effective_date)"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON pension_estimate_history TO hearthledger_app"
    )

    # Backfill one row per existing pension, effective from its creation date.
    op.execute("""
        INSERT INTO pension_estimate_history (
            pension_account_id, effective_date, monthly_benefit_estimate,
            cola_adjustment_rate, survivor_benefit_percent, eligibility_date, created_at
        )
        SELECT
            id, created_at::date, monthly_benefit_estimate,
            cola_adjustment_rate, survivor_benefit_percent, eligibility_date, now()
        FROM pension_accounts
    """)


def downgrade() -> None:
    op.execute("DROP TABLE pension_estimate_history")
