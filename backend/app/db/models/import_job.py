import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

IMPORT_FORMATS = ("csv", "ofx", "qfx")
JOB_STATUSES = ("pending", "processing", "complete", "failed")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(
        Enum(*IMPORT_FORMATS, name="import_format", create_type=False), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(*JOB_STATUSES, name="job_status", create_type=False),
        nullable=False,
        default="pending",
    )
    records_found: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_imported: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_skipped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
