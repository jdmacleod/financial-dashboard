import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, LargeBinary, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CapitalCommitment(Base):
    """A private-fund commitment with drawn/undrawn capital.

    Capital calls increase `called_to_date` and post a `capital_call` transfer;
    distributions post as `capital_distribution` inflows. `nav_account_id`
    points at the `private_fund` account holding current NAV. `fund_name_enc`
    is AES-256-GCM encrypted (named `*_enc` so the audit snapshot excludes it).
    """

    __tablename__ = "capital_commitment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    fund_name_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    called_to_date: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0")
    )
    nav_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    vintage_year: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
