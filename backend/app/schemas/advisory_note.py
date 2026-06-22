import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
