"""Add households.filing_status and households.state (identity layer).

Two nullable household-level identity attributes that a future federal/state
tax-estimate engine will consume:

  filing_status -- IRS filing status enum (single / MFJ / MFS / HoH / QSS)
  state         -- two-letter US state (or DC) of residence

Both are NULL by default with no backfill: filing status and residence are
personal facts not derivable from existing data. They have no consumer yet, so
nothing reads them until the tax engine lands.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-25
"""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

_FILING_STATUSES = (
    "single",
    "married_filing_jointly",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
)


def upgrade() -> None:
    op.execute("CREATE TYPE filing_status AS ENUM " + str(_FILING_STATUSES))
    op.add_column(
        "households",
        sa.Column(
            "filing_status",
            sa.Enum(*_FILING_STATUSES, name="filing_status", create_type=False),
            nullable=True,
        ),
    )
    op.add_column("households", sa.Column("state", sa.String(2), nullable=True))


def downgrade() -> None:
    op.drop_column("households", "state")
    op.drop_column("households", "filing_status")
    op.execute("DROP TYPE IF EXISTS filing_status")
