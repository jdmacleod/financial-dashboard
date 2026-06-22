import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    # ORM attribute is `policy_metadata` (column "metadata"); expose as "metadata".
    metadata: dict[str, Any] = Field(
        validation_alias="policy_metadata", serialization_alias="metadata"
    )
    created_at: datetime
