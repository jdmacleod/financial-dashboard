import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import or_

from app.core.visibility import VisibilityContext
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import Account


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
