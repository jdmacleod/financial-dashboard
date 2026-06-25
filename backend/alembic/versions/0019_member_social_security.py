"""Add household_members Social Security fields.

Two nullable per-member fields so a member's Social Security claiming plan can feed
FIRE projections:

  ss_monthly_benefit_at_fra  -- the member's PIA (estimated monthly benefit at FRA)
  ss_claiming_age            -- the age (62-70) they plan to claim

Both NULL by default (a personal estimate, not derivable). No backfill.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "household_members",
        sa.Column("ss_monthly_benefit_at_fra", sa.Numeric(18, 4), nullable=True),
    )
    op.add_column(
        "household_members",
        sa.Column("ss_claiming_age", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("household_members", "ss_claiming_age")
    op.drop_column("household_members", "ss_monthly_benefit_at_fra")
