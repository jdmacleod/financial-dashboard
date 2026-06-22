import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models.ownership_entity import OWNERSHIP_ENTITY_TYPES

EntityTypeLiteral = str


class OwnershipEntityCreate(BaseModel):
    entity_type: str = Field(..., pattern=f"^({'|'.join(OWNERSHIP_ENTITY_TYPES)})$")
    name: str = Field(..., min_length=1, max_length=200)
    grantor_member_id: uuid.UUID | None = None
    is_in_taxable_estate: bool = True
    counts_in_personal_net_worth: bool = True


class OwnershipEntityUpdate(BaseModel):
    entity_type: str | None = Field(default=None, pattern=f"^({'|'.join(OWNERSHIP_ENTITY_TYPES)})$")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    grantor_member_id: uuid.UUID | None = None
    is_in_taxable_estate: bool | None = None
    counts_in_personal_net_worth: bool | None = None


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
