from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ExportType = Literal["pdf_summary", "pdf_executor", "excel_summary", "excel_executor"]
JobStatus = Literal["pending", "processing", "complete", "failed"]


class ExportCreate(BaseModel):
    export_type: ExportType
    from_date: date
    to_date: date
    account_ids: list[uuid.UUID] | None = None
    include_transactions: bool | None = None


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    export_type: ExportType
    anonymized: bool
    parameters: dict[str, Any]
    status: JobStatus
    filename: str | None
    error_message: str | None
    generated_by: uuid.UUID
    created_at: datetime
    completed_at: datetime | None


class ExportCreateResponse(BaseModel):
    export_job_id: uuid.UUID
