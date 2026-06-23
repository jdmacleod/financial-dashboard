"""Add investment_lot.asset_class for the holdings-mix breakdown.

The Investments page rolls cost-basis lots up into a "Holdings mix by asset
class" donut. This adds a nullable asset_class column (existing lots stay
unclassified). The enum mirrors LOT_ASSET_CLASSES in the model.
"""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE lot_asset_class AS ENUM (
            'equity', 'fixed_income', 'cash', 'real_estate', 'alternative', 'other'
        )
        """
    )
    op.add_column(
        "investment_lot",
        sa.Column(
            "asset_class",
            sa.Enum(
                "equity",
                "fixed_income",
                "cash",
                "real_estate",
                "alternative",
                "other",
                name="lot_asset_class",
                create_type=False,
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("investment_lot", "asset_class")
    op.execute("DROP TYPE IF EXISTS lot_asset_class")
