import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

LOT_BASIS_TYPES = (
    "purchase",
    "rsu_vest",
    "espp",
    "inherited_stepup",
    "gift_carryover",
    "reinvested_dividend",
)


class InvestmentLot(Base):
    """Cost-basis lot for an individual security within an investment account.

    Lot-level basis is the prerequisite for concentration reporting, holding-
    period (LTCG vs STCG) logic, and tax-aware selling. Broadly diversified
    fund accounts may carry a single synthetic lot. `inherited_stepup` carries
    the basis stepped up at a decedent's death.
    """

    __tablename__ = "investment_lot"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    shares: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    basis_per_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    acquired_date: Mapped[date] = mapped_column(Date, nullable=False)
    basis_type: Mapped[str] = mapped_column(
        Enum(*LOT_BASIS_TYPES, name="lot_basis_type", create_type=False),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
