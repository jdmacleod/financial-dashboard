import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    previous_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    user_id: uuid.UUID | None
    user_display_name: str | None
    context: dict[str, Any]
    ip_address: str | None
    created_at: datetime


class PaginatedAuditLog(BaseModel):
    items: list[AuditLogEntryResponse]
    page: int
    page_size: int
    total: int
