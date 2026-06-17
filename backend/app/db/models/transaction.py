import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ARRAY, Boolean, Date, DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

TRANSACTION_SOURCES = ("manual", "csv", "ofx", "qfx")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    real_estate_property_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    post_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    payee_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payee_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_pair_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    source: Mapped[str] = mapped_column(
        Enum(*TRANSACTION_SOURCES, name="transaction_source", create_type=False),
        nullable=False,
        default="manual",
    )
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
