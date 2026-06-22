import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, audit
from app.core.visibility import VisibilityContext
from app.db.models.equity_grant import VestingEvent
from app.db.models.investment_lot import InvestmentLot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository


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
