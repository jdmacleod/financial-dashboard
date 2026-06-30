"""Convert transactions.source enum -> VARCHAR + CHECK; add transactions.confidence.

Postgres cannot drop a value from an enum type, so adding the offline-ingest
sources (json/pdf/ingest) to the ``transaction_source`` enum would be
irreversible. We instead convert the column to VARCHAR + a CHECK constraint
(eng review Issue 4): adding a source is now a CHECK edit, and the migration has
a real downgrade(). ``confidence`` carries the ingest parser's self-assessment.

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-30
"""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None

_ALL_SOURCES = ("manual", "csv", "ofx", "qfx", "json", "pdf", "ingest")
_LEGACY_SOURCES = ("manual", "csv", "ofx", "qfx")
_CHECK_NAME = "ck_transactions_source"


def upgrade() -> None:
    # The column DEFAULT ('manual'::transaction_source) depends on the enum type,
    # so drop it before the type can be dropped, then re-add a plain-text default.
    op.execute("ALTER TABLE transactions ALTER COLUMN source DROP DEFAULT")
    op.alter_column(
        "transactions",
        "source",
        type_=sa.String(16),
        existing_nullable=False,
        postgresql_using="source::text",
    )
    op.execute("DROP TYPE transaction_source")
    op.execute("ALTER TABLE transactions ALTER COLUMN source SET DEFAULT 'manual'")

    allowed = ", ".join(f"'{s}'" for s in _ALL_SOURCES)
    op.create_check_constraint(_CHECK_NAME, "transactions", f"source IN ({allowed})")

    op.add_column(
        "transactions",
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "confidence")
    op.drop_constraint(_CHECK_NAME, "transactions", type_="check")

    # Rows using the new sources can't cast back into the legacy enum; fold them
    # to 'manual' first (mirrors the reclassify-before-cast pattern in 0005/0007).
    # Values are hardcoded module constants, not user input.
    new_sources = ", ".join(f"'{s}'" for s in _ALL_SOURCES if s not in _LEGACY_SOURCES)
    # Interpolated values are fixed module constants, not user input.
    op.execute(
        f"UPDATE transactions SET source = 'manual' WHERE source IN ({new_sources})"  # noqa: S608
    )

    op.execute("ALTER TABLE transactions ALTER COLUMN source DROP DEFAULT")
    legacy = ", ".join(f"'{s}'" for s in _LEGACY_SOURCES)
    op.execute(f"CREATE TYPE transaction_source AS ENUM ({legacy})")
    op.alter_column(
        "transactions",
        "source",
        type_=sa.Enum(*_LEGACY_SOURCES, name="transaction_source"),
        existing_nullable=False,
        postgresql_using="source::transaction_source",
    )
    op.execute("ALTER TABLE transactions ALTER COLUMN source SET DEFAULT 'manual'")
