import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

OWNERSHIP_ENTITY_TYPES = (
    "revocable_trust",
    "irrevocable_trust",
    "ilit",
    "crt_crat",
    "crt_crut",
    "clt",
    "llc",
    "custodial_utma",
    "custodial_ugma",
)


class OwnershipEntity(Base):
    """Trust / titling layer linkable from accounts and real_estate_properties.

    `counts_in_personal_net_worth` and `is_in_taxable_estate` drive the
    net-worth and estate-exposure aggregations: a revocable trust is a pure
    titling layer (both true), whereas an ILIT/CRT holds assets outside both.
    `name_enc` is AES-256-GCM encrypted PII (named `*_enc` so the audit
    snapshot excludes it — see core/audit.py ENCRYPTED_FIELDS).
    """

    __tablename__ = "ownership_entity"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        Enum(*OWNERSHIP_ENTITY_TYPES, name="ownership_entity_type", create_type=False),
        nullable=False,
    )
    name_enc: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    grantor_member_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_in_taxable_estate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    counts_in_personal_net_worth: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
