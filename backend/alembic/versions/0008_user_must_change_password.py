"""Add users.must_change_password for provisioned temporary passwords.

A user provisioned by a primary/partner (via POST /members/provision) is created
with a server-generated temporary password and must_change_password = true; they
are forced to set their own password on first login, which clears the flag.
"""

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
