import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.equity_grant import EquityGrant, VestingEvent
from app.db.models.investment_lot import InvestmentLot
from app.db.models.member import HouseholdMember
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.schemas.equity_grant import (
    EquityGrantCreate,
    EquityGrantResponse,
    EquityGrantUpdate,
    VestingEventResponse,
)


@dataclass
class VestingEventInput:
    account_id: uuid.UUID  # brokerage account receiving the retained shares
    equity_grant_id: uuid.UUID
    event_date: date
    shares_vested: Decimal
    fmv_at_event: Decimal
    ticker: str
    shares_sold_to_cover: Decimal = Decimal("0")
    basis_type: str = "rsu_vest"
    amt_preference_amount: Decimal | None = None
    income_category_id: uuid.UUID | None = None
    sell_to_cover_category_id: uuid.UUID | None = None


class EquityCompService:
    """Records equity-compensation vesting/exercise events.

    A vesting event atomically: posts the taxable-income transaction, posts the
    sell-to-cover withholding transfer, creates the cost-basis lot for retained
    shares, and writes the VestingEvent — all in one commit through the @audit
    method (spec Phase A AC #5).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    async def list_grants(
        self, ctx: VisibilityContext, *, member_id: uuid.UUID | None = None
    ) -> list[EquityGrantResponse]:
        """Equity grants for the household (optionally one member), each with its
        vesting events embedded.
        """
        gq = select(EquityGrant).where(EquityGrant.household_id == ctx.household_id)
        if member_id is not None:
            gq = gq.where(EquityGrant.member_id == member_id)
        gq = gq.order_by(EquityGrant.grant_date)
        grants = list((await self.session.execute(gq)).scalars().all())
        if not grants:
            return []

        grant_ids = [g.id for g in grants]
        events = list(
            (
                await self.session.execute(
                    select(VestingEvent)
                    .where(VestingEvent.equity_grant_id.in_(grant_ids))
                    .order_by(VestingEvent.event_date)
                )
            )
            .scalars()
            .all()
        )
        events_by_grant: dict[uuid.UUID, list[VestingEventResponse]] = {}
        for e in events:
            events_by_grant.setdefault(e.equity_grant_id, []).append(
                VestingEventResponse.model_validate(e)
            )

        return [
            EquityGrantResponse(
                id=g.id,
                household_id=g.household_id,
                member_id=g.member_id,
                grant_type=g.grant_type,
                grant_date=g.grant_date,
                shares_granted=g.shares_granted,
                strike_price=g.strike_price,
                ticker=g.ticker,
                vesting_schedule=g.vesting_schedule,
                espp_discount_pct=g.espp_discount_pct,
                espp_lookback=g.espp_lookback,
                created_at=g.created_at,
                vesting_events=events_by_grant.get(g.id, []),
            )
            for g in grants
        ]

    async def get_grant(self, ctx: VisibilityContext, grant_id: uuid.UUID) -> EquityGrant:
        result = await self.session.execute(
            select(EquityGrant).where(
                EquityGrant.id == grant_id,
                EquityGrant.household_id == ctx.household_id,
            )
        )
        grant = result.scalar_one_or_none()
        if grant is None:
            raise HTTPException(status_code=404, detail="Equity grant not found")
        return grant

    async def grant_response(
        self, ctx: VisibilityContext, grant: EquityGrant
    ) -> EquityGrantResponse:
        """Build the response for a single grant, embedding its vesting events."""
        events = list(
            (
                await self.session.execute(
                    select(VestingEvent)
                    .where(VestingEvent.equity_grant_id == grant.id)
                    .order_by(VestingEvent.event_date)
                )
            )
            .scalars()
            .all()
        )
        return EquityGrantResponse(
            id=grant.id,
            household_id=grant.household_id,
            member_id=grant.member_id,
            grant_type=grant.grant_type,
            grant_date=grant.grant_date,
            shares_granted=grant.shares_granted,
            strike_price=grant.strike_price,
            ticker=grant.ticker,
            vesting_schedule=grant.vesting_schedule,
            espp_discount_pct=grant.espp_discount_pct,
            espp_lookback=grant.espp_lookback,
            created_at=grant.created_at,
            vesting_events=[VestingEventResponse.model_validate(e) for e in events],
        )

    async def _validate_member(self, ctx: VisibilityContext, member_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(HouseholdMember.id).where(
                HouseholdMember.id == member_id,
                HouseholdMember.household_id == ctx.household_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="member_id not in household")

    @audit("equity_grant.created", "equity_grant")
    async def create_grant(self, ctx: VisibilityContext, data: EquityGrantCreate) -> EquityGrant:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self._validate_member(ctx, data.member_id)
        grant = EquityGrant(
            household_id=ctx.household_id,
            member_id=data.member_id,
            grant_type=data.grant_type,
            grant_date=data.grant_date,
            shares_granted=data.shares_granted,
            strike_price=data.strike_price,
            ticker=data.ticker,
            vesting_schedule=data.vesting_schedule,
            espp_discount_pct=data.espp_discount_pct,
            espp_lookback=data.espp_lookback,
            created_at=datetime.now(UTC),
        )
        self.session.add(grant)
        await self.session.flush()
        await self.session.refresh(grant)
        return grant

    @audit("equity_grant.updated", "equity_grant")
    async def update_grant(
        self, ctx: VisibilityContext, grant_id: uuid.UUID, data: EquityGrantUpdate
    ) -> EquityGrant:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        grant = await self.get_grant(ctx, grant_id)
        self._prev_snapshot = _snapshot(grant)
        if data.grant_type is not None:
            grant.grant_type = data.grant_type
        if data.grant_date is not None:
            grant.grant_date = data.grant_date
        if data.shares_granted is not None:
            grant.shares_granted = data.shares_granted
        if data.strike_price is not None:
            grant.strike_price = data.strike_price
        if data.ticker is not None:
            grant.ticker = data.ticker
        if data.vesting_schedule is not None:
            grant.vesting_schedule = data.vesting_schedule
        if data.espp_discount_pct is not None:
            grant.espp_discount_pct = data.espp_discount_pct
        if data.espp_lookback is not None:
            grant.espp_lookback = data.espp_lookback
        await self.session.flush()
        await self.session.refresh(grant)
        return grant

    async def delete_grant(self, ctx: VisibilityContext, grant_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        grant = await self.get_grant(ctx, grant_id)
        # Vesting events carry posted income transactions and cost-basis lots;
        # refuse to delete a grant that still has them rather than cascade away
        # real financial history.
        event_count = await self.session.execute(
            select(func.count())
            .select_from(VestingEvent)
            .where(VestingEvent.equity_grant_id == grant_id)
        )
        if int(event_count.scalar_one()) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a grant with recorded vesting events",
            )
        prev = _snapshot(grant)
        await self.session.delete(grant)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="equity_grant.deleted",
            entity_type="equity_grant",
            entity_id=grant_id,
            previous_value=prev,
        )

    @audit("equity.vesting_recorded", "vesting_event")
    async def record_vesting_event(
        self, ctx: VisibilityContext, data: VestingEventInput
    ) -> VestingEvent:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # Enforce visibility on the target account.
        await self.account_repo.get_by_id(ctx, data.account_id)

        now = datetime.now(UTC)
        taxable_income = data.shares_vested * data.fmv_at_event
        retained = data.shares_vested - data.shares_sold_to_cover

        lot_id: uuid.UUID | None = None
        if retained > 0:
            lot = InvestmentLot(
                account_id=data.account_id,
                ticker=data.ticker,
                shares=retained,
                basis_per_share=data.fmv_at_event,
                acquired_date=data.event_date,
                basis_type=data.basis_type,
                created_at=now,
            )
            self.session.add(lot)
            await self.session.flush()
            lot_id = lot.id

        # Income transaction (inflow) for the full vested value.
        self.session.add(
            Transaction(
                account_id=data.account_id,
                transaction_date=data.event_date,
                amount=taxable_income,
                payee_normalized=f"{data.ticker} vest",
                memo=f"{data.ticker} equity vest",
                category_id=data.income_category_id,
                is_transfer=False,
                tags=["equity_comp"],
                source="manual",
                is_reviewed=True,
                created_at=now,
                updated_at=now,
            )
        )

        # Sell-to-cover withholding (transfer out).
        if data.shares_sold_to_cover > 0:
            self.session.add(
                Transaction(
                    account_id=data.account_id,
                    transaction_date=data.event_date,
                    amount=-(data.shares_sold_to_cover * data.fmv_at_event),
                    payee_normalized=f"{data.ticker} sell-to-cover",
                    memo=f"{data.ticker} sell-to-cover withholding",
                    category_id=data.sell_to_cover_category_id,
                    is_transfer=True,
                    tags=["equity_comp"],
                    source="manual",
                    is_reviewed=True,
                    created_at=now,
                    updated_at=now,
                )
            )

        event = VestingEvent(
            equity_grant_id=data.equity_grant_id,
            event_date=data.event_date,
            shares_vested=data.shares_vested,
            fmv_at_event=data.fmv_at_event,
            taxable_ordinary_income=taxable_income,
            amt_preference_amount=data.amt_preference_amount,
            shares_sold_to_cover=data.shares_sold_to_cover,
            resulting_lot_id=lot_id,
            created_at=now,
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event
