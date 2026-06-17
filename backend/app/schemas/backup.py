from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackupJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    triggered_by: str
    triggered_by_user_id: uuid.UUID | None
    status: str
    filename: str | None
    file_size_bytes: int | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
