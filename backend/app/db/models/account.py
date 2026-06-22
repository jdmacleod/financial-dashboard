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
    # Demo-data extension (migration 0007)
    "inherited_ira",
    "sbloc",
    "margin",
    "private_fund",
    "life_insurance_cash_value",
    "treasury",
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
    # When set, the asset is titled in this entity rather than owned
    # individually/jointly. Net-worth and estate-exposure aggregations respect
    # the entity's counts_in_personal_net_worth / is_in_taxable_estate flags.
    ownership_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Revolving borrowing accounts (sbloc, margin) carry a negative balance with
    # interest accrual but no amortization schedule — the debt-payoff projector
    # skips an amortization curve for these.
    is_revolving: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
