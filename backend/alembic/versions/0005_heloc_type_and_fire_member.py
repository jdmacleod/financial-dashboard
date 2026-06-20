"""Add heloc account type and member_id to fire_scenarios.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-20
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extend the account_type enum with the heloc value.
    # ALTER TYPE ... ADD VALUE runs fine inside a transaction on PostgreSQL 12+;
    # the new value is visible to subsequent transactions after this one commits.
    op.execute("ALTER TYPE account_type ADD VALUE IF NOT EXISTS 'heloc' AFTER 'personal_loan'")

    # Add nullable member_id FK to fire_scenarios so scenarios can be attributed
    # to a specific household member (e.g. "Retire at 60 — Darius's plan").
    op.execute("""
        ALTER TABLE fire_scenarios
            ADD COLUMN member_id UUID REFERENCES household_members(id) ON DELETE SET NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE fire_scenarios DROP COLUMN member_id")
    # PostgreSQL does not support removing enum values once added.
    # To fully reverse, recreate the enum without 'heloc' and update the column.
    op.execute("""
        ALTER TABLE accounts
            ALTER COLUMN account_type TYPE TEXT
    """)
    op.execute("DROP TYPE account_type")
    op.execute("""
        CREATE TYPE account_type AS ENUM (
            'checking', 'savings', 'credit_card',
            'investment_brokerage',
            'retirement_401k', 'retirement_403b', 'retirement_ira', 'retirement_roth_ira',
            'pension', 'hsa',
            'real_estate', 'mortgage', 'auto_loan', 'personal_loan', 'student_loan',
            'other_asset', 'other_liability'
        )
    """)
    op.execute("""
        ALTER TABLE accounts
            ALTER COLUMN account_type TYPE account_type
            USING account_type::account_type
    """)
    op.execute("GRANT USAGE ON TYPE account_type TO hearthledger_app")
