"""Add staging_transactions (ingested-but-unreviewed rows).

A separate table from ``transactions`` so staged rows can never be summed into
account balances or net worth before a human promotes them (T5). A partial
unique index on (account_id, external_id) makes a CLI batch retry idempotent.

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "staging_transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("post_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("payee_raw", sa.String(255), nullable=True),
        sa.Column("memo", sa.String(500), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_staging_transactions_account_id",
        "staging_transactions",
        ["account_id"],
    )
    op.create_index(
        "ix_staging_transactions_batch_id",
        "staging_transactions",
        ["batch_id"],
    )
    op.create_index(
        "uq_staging_account_external_id",
        "staging_transactions",
        ["account_id", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_staging_account_external_id", table_name="staging_transactions")
    op.drop_index("ix_staging_transactions_batch_id", table_name="staging_transactions")
    op.drop_index("ix_staging_transactions_account_id", table_name="staging_transactions")
    op.drop_table("staging_transactions")
