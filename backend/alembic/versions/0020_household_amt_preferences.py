"""Add households.amt_salt_preference and households.amt_iso_preference.

Two nullable household-level AMT preference inputs that feed the §55 alternative
minimum tax in the tax-estimate engine:

  amt_salt_preference -- estimated annual state/local taxes added back for AMT
                         (an AMT preference only when you itemize for regular tax)
  amt_iso_preference  -- estimated annual incentive-stock-option exercise spread
                         (the bargain element, an AMT preference in the year of
                         exercise)

Both are NULL by default with no backfill: AMT preference items are personal
facts not derivable from the ledger. The cash-flow report sums them into the
`amt_preference_income` it passes to `estimate_federal_tax`, so a household that
sets them can finally see a non-zero AMT line. Stored as NUMERIC(18,4) per the
money convention.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-29
"""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "households", sa.Column("amt_salt_preference", sa.Numeric(18, 4), nullable=True)
    )
    op.add_column(
        "households", sa.Column("amt_iso_preference", sa.Numeric(18, 4), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("households", "amt_iso_preference")
    op.drop_column("households", "amt_salt_preference")
