"""Add household_members.retirement_target_age.

A nullable smallint holding the age a member plans to retire. Its first consumer
is the milestone timeline, which renders a "Target retirement" event at
date_of_birth + retirement_target_age years when the value is set. NULL means the
member hasn't chosen a target; no backfill (the value is a personal preference,
not derivable from existing data).
"""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "household_members",
        sa.Column("retirement_target_age", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("household_members", "retirement_target_age")
