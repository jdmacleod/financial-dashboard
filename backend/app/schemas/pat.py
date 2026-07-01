import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PATCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    # Optional override; falls back to settings.pat_default_ttl_days.
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class PATResponse(BaseModel):
    """A PAT as listed in the SPA. Never carries the secret."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prefix: str
    label: str
    capability: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class PATCreatedResponse(PATResponse):
    """Returned exactly once at creation, including the full plaintext token."""

    token: str
