import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.advisory_note import ADVISORY_NOTE_CATEGORIES

_CATEGORY_PATTERN = f"^({'|'.join(ADVISORY_NOTE_CATEGORIES)})$"


class AdvisoryNoteCreate(BaseModel):
    account_id: uuid.UUID | None = None
    ownership_entity_id: uuid.UUID | None = None
    category: str = Field(..., pattern=_CATEGORY_PATTERN)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)


class AdvisoryNoteUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    ownership_entity_id: uuid.UUID | None = None
    category: str | None = Field(default=None, pattern=_CATEGORY_PATTERN)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)


class AdvisoryNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    household_id: uuid.UUID
    account_id: uuid.UUID | None
    ownership_entity_id: uuid.UUID | None
    category: str
    title: str
    body: str
    created_at: datetime
