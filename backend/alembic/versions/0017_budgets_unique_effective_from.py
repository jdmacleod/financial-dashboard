"""Add unique constraint on (household_id, category_id, effective_from) for budgets.

Prevents two budgets for the same category sharing a start date. Previously this
was enforced only by application logic (last-wins), so a race could create
duplicates that the budget-vs-actuals report would silently discard.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-25
"""

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None

_CONSTRAINT = "uq_budgets_household_category_effective_from"


def upgrade() -> None:
    # Defensively remove any pre-existing duplicates before adding the constraint,
    # keeping the most recently created row per (household, category, start date).
    # The report layer already treats later rows as authoritative, so keeping the
    # newest id is behavior-preserving.
    op.execute(
        """
        DELETE FROM budgets b
        USING (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY household_id, category_id, effective_from
                       ORDER BY id DESC
                   ) AS rn
            FROM budgets
        ) dup
        WHERE b.id = dup.id AND dup.rn > 1
        """
    )
    op.create_unique_constraint(
        _CONSTRAINT,
        "budgets",
        ["household_id", "category_id", "effective_from"],
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT, "budgets", type_="unique")
