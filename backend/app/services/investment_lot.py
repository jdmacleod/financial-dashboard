import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.investment_lot import InvestmentLot
from app.repositories.account import AccountRepository
from app.schemas.investment_lot import (
    HoldingsMixSlice,
    InvestmentLotCreate,
    InvestmentLotUpdate,
    PositionRollup,
    PositionsSummary,
)

# Currency convention: NUMERIC(18,4). Lot cost = shares(6dp) * price(6dp) carries
# excess precision, so quantize the rollup to 4 places for clean, consistent output.
_CENTS = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return value.quantize(_CENTS)


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
            asset_class=data.asset_class,
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
        if data.asset_class is not None:
            lot.asset_class = data.asset_class
        await self.session.flush()
        await self.session.refresh(lot)
        return lot

    async def positions_summary(self, ctx: VisibilityContext) -> PositionsSummary:
        """Roll up every visible lot into per-ticker positions and an
        asset-class mix. Cost basis = sum(shares * basis_per_share)."""
        lots = await self.list_lots(ctx)

        by_ticker: dict[str, dict[str, Decimal]] = {}
        by_class: dict[str, Decimal] = {}
        total = Decimal("0")
        for lot in lots:
            cost = lot.shares * lot.basis_per_share
            total += cost
            agg = by_ticker.setdefault(
                lot.ticker,
                {"shares": Decimal("0"), "cost_basis": Decimal("0"), "lot_count": Decimal("0")},
            )
            agg["shares"] += lot.shares
            agg["cost_basis"] += cost
            agg["lot_count"] += 1
            klass = lot.asset_class or "unclassified"
            by_class[klass] = by_class.get(klass, Decimal("0")) + cost

        positions = sorted(
            (
                PositionRollup(
                    ticker=ticker,
                    shares=agg["shares"],
                    cost_basis=_money(agg["cost_basis"]),
                    lot_count=int(agg["lot_count"]),
                )
                for ticker, agg in by_ticker.items()
            ),
            key=lambda p: p.cost_basis,
            reverse=True,
        )
        holdings_mix = sorted(
            (
                HoldingsMixSlice(
                    asset_class=klass,
                    cost_basis=_money(cost),
                    percentage=float(cost / total * 100) if total > 0 else 0.0,
                )
                for klass, cost in by_class.items()
            ),
            key=lambda s: s.cost_basis,
            reverse=True,
        )
        return PositionsSummary(
            positions=positions, holdings_mix=holdings_mix, total_cost_basis=_money(total)
        )

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
