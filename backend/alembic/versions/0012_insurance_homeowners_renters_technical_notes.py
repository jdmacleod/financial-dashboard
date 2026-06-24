"""Add homeowners/renters policy types, technical_notes, and insured_real_estate_id.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE commits immediately in PG12+ even inside a txn;
    # IF NOT EXISTS makes it safe to re-run.
    op.execute(
        "ALTER TYPE insurance_policy_type ADD VALUE IF NOT EXISTS 'homeowners' AFTER 'scheduled_specialty'"
    )
    op.execute(
        "ALTER TYPE insurance_policy_type ADD VALUE IF NOT EXISTS 'renters' AFTER 'homeowners'"
    )

    op.add_column("insurance_policy", sa.Column("technical_notes", sa.Text(), nullable=True))
    op.add_column(
        "insurance_policy",
        sa.Column("insured_real_estate_id", sa.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    # Postgres does not support DROP VALUE for enum types; homeowners/renters
    # values remain after downgrade but are harmless (no rows will reference them).
    op.drop_column("insurance_policy", "insured_real_estate_id")
    op.drop_column("insurance_policy", "technical_notes")
