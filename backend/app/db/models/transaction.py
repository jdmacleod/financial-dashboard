import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ARRAY, Boolean, Date, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Stored as VARCHAR + CHECK (not a PG enum) so new sources are addable with a
# reversible migration — Postgres can't drop an enum value (eng review Issue 4).
# 'json'/'pdf'/'ingest' are the offline-ingest sources.
TRANSACTION_SOURCES = ("manual", "csv", "ofx", "qfx", "json", "pdf", "ingest")


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
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    # Parser self-assessment for ingested rows (1.0 deterministic; the model's
    # score for LLM-parsed PDF). NULL for manual/legacy rows.
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
