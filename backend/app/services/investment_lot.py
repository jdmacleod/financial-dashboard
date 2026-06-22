import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.investment_lot import InvestmentLot
from app.repositories.account import AccountRepository
from app.schemas.investment_lot import InvestmentLotCreate, InvestmentLotUpdate


class InvestmentLotService:
    """Read/write access to cost-basis lots. Lots belong to accounts, so
    visibility is enforced through AccountRepository.get_visible / get_by_id: a
    member only sees and edits lots in accounts they can see.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.audit_repo = AuditRepository(session)

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

    async def get_by_id(self, ctx: VisibilityContext, lot_id: uuid.UUID) -> InvestmentLot:
        result = await self.session.execute(select(InvestmentLot).where(InvestmentLot.id == lot_id))
        lot = result.scalar_one_or_none()
        if lot is None:
            raise HTTPException(status_code=404, detail="Investment lot not found")
        # Enforce account visibility: 404 if the lot's account is not visible.
        await self.account_repo.get_by_id(ctx, lot.account_id)
        return lot

    @audit("investment_lot.created", "investment_lot")
    async def create(self, ctx: VisibilityContext, data: InvestmentLotCreate) -> InvestmentLot:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # Raises 404 if the target account is not visible to this context.
        await self.account_repo.get_by_id(ctx, data.account_id)
        lot = InvestmentLot(
            account_id=data.account_id,
            ticker=data.ticker,
            shares=data.shares,
            basis_per_share=data.basis_per_share,
            acquired_date=data.acquired_date,
            basis_type=data.basis_type,
            created_at=datetime.now(UTC),
        )
        self.session.add(lot)
        await self.session.flush()
        await self.session.refresh(lot)
        return lot

    @audit("investment_lot.updated", "investment_lot")
    async def update(
        self, ctx: VisibilityContext, lot_id: uuid.UUID, data: InvestmentLotUpdate
    ) -> InvestmentLot:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        lot = await self.get_by_id(ctx, lot_id)
        self._prev_snapshot = _snapshot(lot)
        if data.ticker is not None:
            lot.ticker = data.ticker
        if data.shares is not None:
            lot.shares = data.shares
        if data.basis_per_share is not None:
            lot.basis_per_share = data.basis_per_share
        if data.acquired_date is not None:
            lot.acquired_date = data.acquired_date
        if data.basis_type is not None:
            lot.basis_type = data.basis_type
        await self.session.flush()
        await self.session.refresh(lot)
        return lot

    async def delete(self, ctx: VisibilityContext, lot_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        lot = await self.get_by_id(ctx, lot_id)
        prev = _snapshot(lot)
        await self.session.delete(lot)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="investment_lot.deleted",
            entity_type="investment_lot",
            entity_id=lot_id,
            previous_value=prev,
        )
