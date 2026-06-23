import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Enum, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

INSURANCE_POLICY_TYPES = (
    "term_life",
    "permanent_life",
    "umbrella_liability",
    "disability",
    "long_term_care",
    "scheduled_specialty",
)

PREMIUM_CADENCES = ("monthly", "quarterly", "annual")


class InsurancePolicy(Base):
    """Coverage record spanning term/permanent life, umbrella, DI, LTC, specialty.

    Permanent (cash-value) policies link to an `accounts` row of type
    `life_insurance_cash_value` via `cash_value_account_id`. When an ILIT owns
    the policy (`owner_ownership_entity_id` set to a non-NW entity), the cash
    value is excluded from personal net worth by the ownership-entity rule.
    """

    __tablename__ = "insurance_policy"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_type: Mapped[str] = mapped_column(
        Enum(*INSURANCE_POLICY_TYPES, name="insurance_policy_type", create_type=False),
        nullable=False,
    )
    insured_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    owner_ownership_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    coverage_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    premium_amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    premium_cadence: Mapped[str] = mapped_column(
        Enum(*PREMIUM_CADENCES, name="premium_cadence", create_type=False),
        nullable=False,
    )
    cash_value_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    policy_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    carrier: Mapped[str | None] = mapped_column(nullable=True)
    policy_number: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
