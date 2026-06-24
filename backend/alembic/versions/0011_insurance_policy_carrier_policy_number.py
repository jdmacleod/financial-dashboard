"""Add carrier and policy_number to insurance_policy.

revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_policy",
        sa.Column("carrier", sa.String(255), nullable=True),
    )
    op.add_column(
        "insurance_policy",
        sa.Column("policy_number", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("insurance_policy", "policy_number")
    op.drop_column("insurance_policy", "carrier")
