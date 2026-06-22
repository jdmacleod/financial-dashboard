import uuid
from datetime import datetime

from pydantic import BaseModel


class OwnershipEntityResponse(BaseModel):
    # name is decrypted in the service layer (stored as name_enc BYTEA), so this
    # response is built explicitly rather than via from_attributes.
    id: uuid.UUID
    household_id: uuid.UUID
    entity_type: str
    name: str
    grantor_member_id: uuid.UUID | None
    is_in_taxable_estate: bool
    counts_in_personal_net_worth: bool
    created_at: datetime
