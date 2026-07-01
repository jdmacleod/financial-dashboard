"""Add personal_access_tokens (programmatic ingest API auth).

A token row stores only the SHA-256 of the secret plus a non-secret indexed
``prefix`` for O(1) lookup. The wire token (hl_pat_<prefix>.<secret>) is shown
once at creation and never persisted. Revocation/expiry are enforced live at
auth time. Minting is primary-only (enforced in PATService).

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-30
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_access_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("household_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("capability", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_personal_access_tokens_prefix",
        "personal_access_tokens",
        ["prefix"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_personal_access_tokens_prefix", table_name="personal_access_tokens")
    op.drop_table("personal_access_tokens")
