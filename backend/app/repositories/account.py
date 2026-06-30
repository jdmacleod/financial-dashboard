import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import or_

from app.core.visibility import VisibilityContext
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import TRANSACTION_BASED_TYPES, Account
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_visible(self, ctx: VisibilityContext, **filters: Any) -> list[Account]:
        """
        THE canonical account query method.
        All code paths that need accounts must call this.
        Never query Account directly outside this class.
        """
        q = select(Account).where(Account.household_id == ctx.household_id)

        if not ctx.is_primary:
            q = q.where(
                or_(
                    Account.owner_member_id.is_(None),
                    Account.owner_member_id == ctx.member_id,
                    Account.id.in_(
                        select(AccountAccessGrant.account_id).where(
                            AccountAccessGrant.grantee_member_id == ctx.member_id,
                            AccountAccessGrant.is_active.is_(True),
                        )
                    ),
                )
            )

        for attr, value in filters.items():
            q = q.where(getattr(Account, attr) == value)

        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_id(self, ctx: VisibilityContext, account_id: uuid.UUID) -> Account:
        accounts = await self.get_visible(ctx, id=account_id)
        if not accounts:
            raise HTTPException(status_code=404, detail="Account not found")
        return accounts[0]

    async def latest_snapshot(self, account_id: uuid.UUID) -> tuple[Decimal, date] | None:
        """Return (balance, snapshot_date) for the most recent snapshot, or None."""
        result = await self.session.execute(
            select(AccountSnapshot.balance, AccountSnapshot.snapshot_date)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.snapshot_date.desc())
            .limit(1)
        )
        row = result.one_or_none()
        if row is None:
            return None
        return Decimal(str(row.balance)), row.snapshot_date

    async def current_balance(self, account: Account) -> tuple[Decimal, date | None] | None:
        """Resolve an account's current balance the SAME way the Accounts ledger
        does: the running SUM of transactions for transaction-based types, the
        latest snapshot otherwise. Returns (balance, as_of) or None when the
        account has no balance data yet. Transaction-based balances have no
        as_of date (they are a live aggregate), hence the optional second slot.

        This is the shared resolver the property-equity calc uses so a linked
        mortgage shows the same balance as it does on the Accounts page —
        previously equity read snapshots only, so a transaction-based mortgage
        with no snapshot reported no balance and the equity bar vanished.
        """
        if account.account_type in TRANSACTION_BASED_TYPES:
            result = await self.session.execute(
                select(func.sum(Transaction.amount)).where(Transaction.account_id == account.id)
            )
            total = result.scalar_one_or_none()
            if total is None:
                return None
            return Decimal(str(total)), None
        return await self.latest_snapshot(account.id)
