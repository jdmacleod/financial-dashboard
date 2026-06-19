import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, LargeBinary, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PROPERTY_TYPE_ENUM = Enum(
    "primary_residence",
    "rental",
    "vacation",
    "commercial",
    "land",
    "other",
    name="property_type",
    create_type=False,
)


class RealEstateProperty(Base):
    __tablename__ = "real_estate_properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    address_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    linked_mortgage_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    property_type: Mapped[str] = mapped_column(
        PROPERTY_TYPE_ENUM, nullable=False, default="primary_residence"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
