import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.investment_lot import InvestmentLot
from app.repositories.account import AccountRepository


class InvestmentLotService:
    """Read access to cost-basis lots. Lots belong to accounts, so visibility is
    enforced through AccountRepository.get_visible: a member only sees lots in
    accounts they can see.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)

    async def list_lots(
        self, ctx: VisibilityContext, *, account_id: uuid.UUID | None = None
    ) -> list[InvestmentLot]:
        if account_id is not None:
            # Raises 404 if the account is not visible to this context.
            await self.account_repo.get_by_id(ctx, account_id)
            visible_ids = [account_id]
        else:
            visible_ids = [a.id for a in await self.account_repo.get_visible(ctx)]
        if not visible_ids:
            return []
        result = await self.session.execute(
            select(InvestmentLot)
            .where(InvestmentLot.account_id.in_(visible_ids))
            .order_by(InvestmentLot.acquired_date)
        )
        return list(result.scalars().all())
