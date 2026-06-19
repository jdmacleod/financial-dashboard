"""Add property_type enum to real_estate_properties.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-18
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE property_type AS ENUM "
        "('primary_residence', 'rental', 'vacation', 'commercial', 'land', 'other')"
    )
    op.execute(
        "ALTER TABLE real_estate_properties "
        "ADD COLUMN property_type property_type NOT NULL DEFAULT 'primary_residence'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE real_estate_properties DROP COLUMN property_type")
    op.execute("DROP TYPE property_type")
