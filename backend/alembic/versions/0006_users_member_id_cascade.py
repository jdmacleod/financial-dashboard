"""users.member_id FK: SET NULL -> CASCADE

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21

Previously, deleting a household_members row left the linked users row alive
(member_id set to NULL). This caused UniqueViolationError on email when the
seed reset action tried to re-insert a user whose household had just been
cascade-deleted. Changing to CASCADE means user accounts are removed when
their household_members record is removed.
"""

from __future__ import annotations

from typing import Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("users_member_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_member_id_fkey",
        "users",
        "household_members",
        ["member_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("users_member_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_member_id_fkey",
        "users",
        "household_members",
        ["member_id"],
        ["id"],
        ondelete="SET NULL",
    )
