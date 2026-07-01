"""Add category_rules (deterministic payee -> category rules).

The memory layer for auto-categorization: on import-promote and manual entry, an
uncategorized transaction takes the category of the highest-priority active rule
whose pattern matches its payee. Rules only fill an empty category.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-01
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

_MATCH_TYPES = ("exact", "contains", "regex")
_CHECK_NAME = "ck_category_rules_match_type"


def upgrade() -> None:
    op.create_table(
        "category_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("household_id", UUID(as_uuid=True), nullable=False),
        sa.Column("pattern", sa.String(255), nullable=False),
        sa.Column("match_type", sa.String(16), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_category_rules_household_id", "category_rules", ["household_id"]
    )
    allowed = ", ".join(f"'{m}'" for m in _MATCH_TYPES)
    op.create_check_constraint(_CHECK_NAME, "category_rules", f"match_type IN ({allowed})")


def downgrade() -> None:
    op.drop_constraint(_CHECK_NAME, "category_rules", type_="check")
    op.drop_index("ix_category_rules_household_id", table_name="category_rules")
    op.drop_table("category_rules")
