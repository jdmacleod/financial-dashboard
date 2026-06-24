"""Add accounts.tax_treatment for RMD eligibility.

Required Minimum Distributions apply only to pretax (traditional) retirement
balances, never to Roth or taxable accounts. This adds a nullable tax_treatment
enum and backfills it from account_type where the treatment is unambiguous:

  pretax  -> retirement_401k, retirement_403b, retirement_ira
  roth    -> retirement_roth_ira
  taxable -> investment_brokerage, treasury

Everything else stays NULL (not applicable / unclassified). Inherited IRAs are
deliberately left NULL: their distributions follow separate beneficiary rules
(10-year, etc.), not the owner Uniform Lifetime Table, so they are out of scope
for the v1 RMD engine. Users can classify accounts explicitly later.
"""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE tax_treatment AS ENUM ('pretax', 'roth', 'taxable')")
    op.add_column(
        "accounts",
        sa.Column(
            "tax_treatment",
            sa.Enum("pretax", "roth", "taxable", name="tax_treatment", create_type=False),
            nullable=True,
        ),
    )
    # Compare account_type as text, not as enum literals: some account_type values
    # (e.g. 'treasury') were added by an earlier migration in the same upgrade
    # transaction, and Postgres forbids using a not-yet-committed enum value as a
    # literal. Casting the column to text sidesteps that entirely.
    op.execute(
        """
        UPDATE accounts SET tax_treatment = 'pretax'
        WHERE account_type::text IN ('retirement_401k', 'retirement_403b', 'retirement_ira')
        """
    )
    op.execute(
        """
        UPDATE accounts SET tax_treatment = 'roth'
        WHERE account_type::text = 'retirement_roth_ira'
        """
    )
    op.execute(
        """
        UPDATE accounts SET tax_treatment = 'taxable'
        WHERE account_type::text IN ('investment_brokerage', 'treasury')
        """
    )


def downgrade() -> None:
    op.drop_column("accounts", "tax_treatment")
    op.execute("DROP TYPE IF EXISTS tax_treatment")
