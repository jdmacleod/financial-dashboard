from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EXPORT_TYPES = ("pdf_summary", "pdf_executor", "excel_summary", "excel_executor")
EXPORT_JOB_STATUSES = ("pending", "processing", "complete", "failed")


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    export_type: Mapped[str] = mapped_column(
        Enum(*EXPORT_TYPES, name="export_type", create_type=False), nullable=False
    )
    anonymized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        Enum(*EXPORT_JOB_STATUSES, name="job_status", create_type=False),
        nullable=False,
        default="pending",
    )
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
