import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.insurance_policy import INSURANCE_POLICY_TYPES, PREMIUM_CADENCES

_POLICY_TYPE_PATTERN = f"^({'|'.join(INSURANCE_POLICY_TYPES)})$"
_CADENCE_PATTERN = f"^({'|'.join(PREMIUM_CADENCES)})$"


class InsurancePolicyCreate(BaseModel):
    policy_type: str = Field(..., pattern=_POLICY_TYPE_PATTERN)
    insured_member_id: uuid.UUID | None = None
    owner_ownership_entity_id: uuid.UUID | None = None
    coverage_amount: Decimal = Field(..., ge=0)
    premium_amount: Decimal = Field(..., ge=0)
    premium_cadence: str = Field(..., pattern=_CADENCE_PATTERN)
    cash_value_account_id: uuid.UUID | None = None
    carrier: str | None = None
    policy_number: str | None = None
    technical_notes: str | None = None
    insured_real_estate_id: uuid.UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InsurancePolicyUpdate(BaseModel):
    policy_type: str | None = Field(default=None, pattern=_POLICY_TYPE_PATTERN)
    insured_member_id: uuid.UUID | None = None
    owner_ownership_entity_id: uuid.UUID | None = None
    coverage_amount: Decimal | None = Field(default=None, ge=0)
    premium_amount: Decimal | None = Field(default=None, ge=0)
    premium_cadence: str | None = Field(default=None, pattern=_CADENCE_PATTERN)
    cash_value_account_id: uuid.UUID | None = None
    carrier: str | None = None
    policy_number: str | None = None
    technical_notes: str | None = None
    insured_real_estate_id: uuid.UUID | None = None
    metadata: dict[str, Any] | None = None


class InsurancePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    household_id: uuid.UUID
    policy_type: str
    insured_member_id: uuid.UUID | None
    owner_ownership_entity_id: uuid.UUID | None
    coverage_amount: Decimal
    premium_amount: Decimal
    premium_cadence: str
    cash_value_account_id: uuid.UUID | None
    carrier: str | None
    policy_number: str | None
    technical_notes: str | None
    insured_real_estate_id: uuid.UUID | None
    # ORM attribute is `policy_metadata` (column "metadata"); expose as "metadata".
    metadata: dict[str, Any] = Field(
        validation_alias="policy_metadata", serialization_alias="metadata"
    )
    created_at: datetime
