import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StagingTransaction(Base):
    """An ingested-but-not-yet-confirmed transaction.

    Staging rows live in their OWN table, never in ``transactions`` (eng review,
    Issue 1): account balances and reports sum ``transactions.amount`` with no
    review filter, so a row in this table CANNOT inflate net worth until a human
    reviews it and it is promoted (T5). That makes the "nothing is trusted until
    reviewed" guarantee structural, not a filter someone can forget.

    ``payee_raw`` / ``memo`` are stored already server-redacted (core/pii.py).
    Idempotency: a partial unique index on (account_id, external_id) makes a CLI
    retry of the same batch a no-op instead of a double-stage.
    """

    __tablename__ = "staging_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Groups one CLI push; client-supplied so a retry reuses it (idempotency).
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    post_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    payee_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_staging_account_external_id",
            "account_id",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )
