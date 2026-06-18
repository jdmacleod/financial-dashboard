import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TransactionCreate(BaseModel):
    transaction_date: date
    amount: Decimal
    payee_normalized: str | None = None
    memo: str | None = None
    category_id: uuid.UUID | None = None
    is_transfer: bool = False
    real_estate_property_id: uuid.UUID | None = None


class TransactionUpdate(BaseModel):
    transaction_date: date | None = None
    amount: Decimal | None = None
    payee_normalized: str | None = None
    memo: str | None = None
    category_id: uuid.UUID | None = None
    is_transfer: bool | None = None
    real_estate_property_id: uuid.UUID | None = None
    is_reviewed: bool | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    real_estate_property_id: uuid.UUID | None
    transaction_date: date
    post_date: date | None
    amount: Decimal
    payee_raw: str | None
    payee_normalized: str | None
    memo: str | None
    category_id: uuid.UUID | None
    is_transfer: bool
    transfer_pair_id: uuid.UUID | None
    tags: list[str]
    source: str
    import_job_id: uuid.UUID | None
    external_id: str | None
    is_reviewed: bool
    created_at: datetime
    updated_at: datetime


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class BulkCategorizeRequest(BaseModel):
    transaction_ids: list[uuid.UUID]
    category_id: uuid.UUID
