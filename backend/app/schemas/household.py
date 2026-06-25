import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

FilingStatus = Literal[
    "single",
    "married_filing_jointly",
    "married_filing_separately",
    "head_of_household",
    "qualifying_surviving_spouse",
]

# 50 states + DC. Two-letter USPS codes; HearthLedger is US/USD-only (v1).
US_STATES: frozenset[str] = frozenset(
    {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
        "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
        "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
        "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
        "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    }
)  # fmt: skip


class HouseholdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    settings: dict[str, Any]
    filing_status: FilingStatus | None = None
    state: str | None = None
    created_at: datetime


class HouseholdUpdate(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None
    filing_status: FilingStatus | None = None
    state: str | None = None

    @field_validator("state")
    @classmethod
    def _validate_state(cls, v: str | None) -> str | None:
        if v is None:
            return None
        code = v.strip().upper()
        if code not in US_STATES:
            raise ValueError("state must be a two-letter US state or DC code")
        return code


class ValuationConfigResponse(BaseModel):
    provider: str
    has_api_key: bool


class ValuationConfigUpdate(BaseModel):
    provider: str
    api_key: str | None = None
