import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    contributed_ytd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    employer_match_ytd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(
        Enum("manual", "import", name="snapshot_source", create_type=False),
        nullable=False,
        default="manual",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
