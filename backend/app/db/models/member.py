import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("primary", "partner", "dependent", name="member_role", create_type=False),
        nullable=False,
        default="partner",
    )
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The age the member plans to retire. Drives the "Target retirement" event on
    # the milestone timeline; NULL when not set.
    retirement_target_age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Social Security claiming plan: PIA (estimated monthly benefit at FRA) and the
    # age the member plans to claim (62-70). Feeds a derived FIRE income stream.
    ss_monthly_benefit_at_fra: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    ss_claiming_age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
