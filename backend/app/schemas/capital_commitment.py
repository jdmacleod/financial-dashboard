import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class CapitalCommitmentResponse(BaseModel):
    # fund_name is decrypted in the service layer (stored as fund_name_enc BYTEA).
    id: uuid.UUID
    household_id: uuid.UUID
    fund_name: str
    committed_amount: Decimal
    called_to_date: Decimal
    nav_account_id: uuid.UUID
    vintage_year: int
    created_at: datetime
