import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ImportFormat = Literal["csv", "ofx", "qfx"]


class ImportPreviewResponse(BaseModel):
    headers: list[str]
    preview_rows: list[list[str]]
    suggested_mapping: dict[str, str]


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    filename: str
    format: ImportFormat
    status: Literal["pending", "processing", "complete", "failed"]
    records_found: int | None
    records_imported: int | None
    records_skipped: int | None
    error_message: str | None
    imported_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
