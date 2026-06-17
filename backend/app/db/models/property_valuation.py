import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, Enum, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

VALUATION_SOURCES = ("manual", "api_attom", "api_estated")


class PropertyValuation(Base):
    __tablename__ = "property_valuations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    real_estate_property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    valuation_date: Mapped[date] = mapped_column(Date, nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source: Mapped[str] = mapped_column(
        Enum(*VALUATION_SOURCES, name="valuation_source", create_type=False),
        nullable=False,
        default="manual",
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    raw_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
