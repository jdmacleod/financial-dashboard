import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

STAGING_SOURCES = ("csv", "json", "pdf", "ingest")


class StagingRow(BaseModel):
    """One canonical, pre-parsed row pushed by the ingest CLI.

    payee_raw / memo may contain whatever the source statement held; the server
    re-redacts PII before persisting (core/pii.py) — the client is not trusted to
    have stripped it. ``confidence`` is the parser's self-assessment (1.0 for
    deterministic CSV/JSON; the model's score for LLM-parsed PDF).
    """

    transaction_date: date
    amount: Decimal
    payee_raw: str | None = Field(default=None, max_length=255)
    memo: str | None = Field(default=None, max_length=500)
    external_id: str | None = Field(default=None, max_length=255)
    source: str = "ingest"
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class ImportStagingRequest(BaseModel):
    # Client-supplied so a retry of the same push is idempotent. Optional: the
    # server generates one when absent.
    batch_id: uuid.UUID | None = None
    rows: list[StagingRow] = Field(min_length=1, max_length=5000)


class StagingRowError(BaseModel):
    index: int
    error: str


class ImportStagingResponse(BaseModel):
    batch_id: uuid.UUID
    staged: int
    skipped_duplicate: int
    failed: int
    errors: list[StagingRowError]


class StagingTransactionResponse(BaseModel):
    """A staged row as shown in the review queue."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    batch_id: uuid.UUID
    transaction_date: date
    post_date: date | None
    amount: Decimal
    payee_raw: str | None
    memo: str | None
    external_id: str | None
    source: str
    confidence: Decimal | None
    created_at: datetime
