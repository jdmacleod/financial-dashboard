import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ADVISORY_NOTE_CATEGORIES = (
    "estate",
    "tax",
    "concentration",
    "insurance",
    "retirement",
    "charitable",
    "scope_omission",
)


class AdvisoryNote(Base):
    """A planning insight persisted as first-class data, optionally anchored to
    an account or ownership entity. The `scope_omission` category records
    intentional out-of-scope boundaries household-by-household.
    """

    __tablename__ = "advisory_note"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    ownership_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    category: Mapped[str] = mapped_column(
        Enum(*ADVISORY_NOTE_CATEGORIES, name="advisory_note_category", create_type=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
