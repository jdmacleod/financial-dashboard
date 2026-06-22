import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EQUITY_GRANT_TYPES = ("rsu", "iso", "nso", "espp")


class EquityGrant(Base):
    """An equity-compensation grant (RSU/ISO/NSO/ESPP) to a member.

    `vesting_schedule` is a JSONB cliff+cadence descriptor. Vesting is realized
    by VestingEvent rows. v1 models vests at net values (gross-salary /
    payroll-deduction detail is deferred to v2 per the spec).
    """

    __tablename__ = "equity_grant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    grant_type: Mapped[str] = mapped_column(
        Enum(*EQUITY_GRANT_TYPES, name="equity_grant_type", create_type=False),
        nullable=False,
    )
    grant_date: Mapped[date] = mapped_column(Date, nullable=False)
    shares_granted: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    strike_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    vesting_schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    espp_discount_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    espp_lookback: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VestingEvent(Base):
    """A single vest/exercise/purchase event under an EquityGrant.

    Posts an income transaction, a sell-to-cover transfer, and creates an
    investment_lot for retained shares (see services/equity_comp.py). ISO
    exercise-and-hold sets `amt_preference_amount`.
    """

    __tablename__ = "vesting_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equity_grant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    shares_vested: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    fmv_at_event: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    taxable_ordinary_income: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    amt_preference_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    shares_sold_to_cover: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0")
    )
    resulting_lot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
