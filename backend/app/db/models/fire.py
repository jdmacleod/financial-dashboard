from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FireScenario(Base):
    __tablename__ = "fire_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_annual_spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    safe_withdrawal_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.04")
    )
    expected_annual_return: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.07")
    )
    expected_inflation_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.03")
    )
    target_retirement_age: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    additional_income_streams: Mapped[Any] = mapped_column(JSON, nullable=False, default=list)
    detected_annual_income: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    detected_annual_expenses: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    detected_savings_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    detected_portfolio_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    detection_trailing_months: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=12)
    detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
