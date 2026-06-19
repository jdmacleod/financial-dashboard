import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, LargeBinary, Numeric, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PensionAccount(Base):
    __tablename__ = "pension_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    plan_name_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    administrator_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    monthly_benefit_estimate: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    eligibility_age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    eligibility_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cola_adjustment_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.02")
    )
    is_vested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vesting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    survivor_benefit_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    notes_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
