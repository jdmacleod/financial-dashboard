"""Add 'quarterly' to the budget_period enum.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-25
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE commits immediately in PG12+ even inside a txn;
    # IF NOT EXISTS makes it safe to re-run. Ordered between monthly and annual.
    op.execute("ALTER TYPE budget_period ADD VALUE IF NOT EXISTS 'quarterly' AFTER 'monthly'")


def downgrade() -> None:
    # Postgres does not support DROP VALUE for enum types; 'quarterly' remains
    # after downgrade but is harmless once no budget rows reference it. Reset any
    # quarterly budgets to monthly first so the value is unreferenced.
    op.execute("UPDATE budgets SET period = 'monthly' WHERE period = 'quarterly'")
