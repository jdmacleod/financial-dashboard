import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# How a rule's pattern is matched against a transaction's payee:
#   exact    -> normalized payee equals the normalized pattern
#   contains -> normalized pattern is a substring of the normalized payee
#   regex    -> pattern is a regular expression searched against the raw payee
RULE_MATCH_TYPES = ("exact", "contains", "regex")


class CategoryRule(Base):
    """A payee -> category rule for automatic (deterministic) categorization.

    Rules are the memory layer behind "HearthLedger remembers this payee": on
    import-promote and on manual entry, an uncategorized transaction gets the
    category of the highest-priority active rule whose pattern matches its payee.
    Rules only ever FILL an empty category — they never overwrite a category a
    human already set (that would fight the trust model). LLM categorization
    (a later release) only ever handles the tail these deterministic rules miss.
    """

    __tablename__ = "category_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    match_type: Mapped[str] = mapped_column(String(16), nullable=False, default="contains")
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Higher wins. Ties broken by created_at (older first) for determinism.
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
