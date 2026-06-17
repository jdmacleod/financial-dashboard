import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SnapshotCreate(BaseModel):
    snapshot_date: date
    balance: Decimal
    contributed_ytd: Decimal | None = None
    employer_match_ytd: Decimal | None = None
    memo: str | None = None


class SnapshotUpdate(BaseModel):
    balance: Decimal | None = None
    contributed_ytd: Decimal | None = None
    employer_match_ytd: Decimal | None = None
    memo: str | None = None


class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    snapshot_date: date
    balance: Decimal
    contributed_ytd: Decimal | None
    employer_match_ytd: Decimal | None
    memo: str | None
    source: str
    created_at: datetime
