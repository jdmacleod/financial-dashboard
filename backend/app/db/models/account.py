import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACCOUNT_TYPES = (
    "checking",
    "savings",
    "credit_card",
    "investment_brokerage",
    "retirement_401k",
    "retirement_403b",
    "retirement_ira",
    "retirement_roth_ira",
    "pension",
    "hsa",
    "real_estate",
    "mortgage",
    "auto_loan",
    "personal_loan",
    "heloc",
    "student_loan",
    "other_asset",
    "other_liability",
)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    owner_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    account_type: Mapped[str] = mapped_column(
        Enum(*ACCOUNT_TYPES, name="account_type", create_type=False),
        nullable=False,
    )
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    account_number_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    routing_number_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    include_in_net_worth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
