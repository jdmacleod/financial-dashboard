import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

AccountType = Literal[
    "checking",
    "savings",
    "credit_card",
    "investment_brokerage",
    "retirement_401k",
    "retirement_403b",
    "retirement_ira",
    "retirement_roth_ira",
    "pension",
    "hsa",
    "real_estate",
    "mortgage",
    "auto_loan",
    "personal_loan",
    "heloc",
    "student_loan",
    "other_asset",
    "other_liability",
]


class AccountCreate(BaseModel):
    account_type: AccountType
    nickname: str
    owner_member_id: uuid.UUID | None = None
    institution_name: str | None = None
    account_number: str | None = None
    routing_number: str | None = None
    include_in_net_worth: bool = True
    notes: Annotated[str | None, Field(max_length=2000)] = None


class AccountUpdate(BaseModel):
    nickname: str | None = None
    owner_member_id: uuid.UUID | None = None
    ownership_entity_id: uuid.UUID | None = None
    institution_name: str | None = None
    account_number: str | None = None
    routing_number: str | None = None
    include_in_net_worth: bool | None = None
    notes: Annotated[str | None, Field(max_length=2000)] = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nickname: str
    account_type: str
    owner_member_id: uuid.UUID | None
    ownership_entity_id: uuid.UUID | None
    institution_name: str | None
    account_number_last4: str | None
    include_in_net_worth: bool
    is_active: bool
    current_balance: Decimal | None
    balance_as_of: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class AccessGrantCreate(BaseModel):
    grantee_member_id: uuid.UUID


class AccessGrantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    owner_member_id: uuid.UUID
    grantee_member_id: uuid.UUID
    access_level: str
    is_active: bool
    created_at: datetime


class SetupRequest(BaseModel):
    household_name: str
    member_name: str
    email: str
    password: str
