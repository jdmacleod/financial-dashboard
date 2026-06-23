import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.investment_lot import LOT_ASSET_CLASSES, LOT_BASIS_TYPES

_BASIS_TYPE_PATTERN = f"^({'|'.join(LOT_BASIS_TYPES)})$"
_ASSET_CLASS_PATTERN = f"^({'|'.join(LOT_ASSET_CLASSES)})$"


class InvestmentLotCreate(BaseModel):
    account_id: uuid.UUID
    ticker: str = Field(..., min_length=1, max_length=16)
    shares: Decimal = Field(..., gt=0)
    basis_per_share: Decimal = Field(..., ge=0)
    acquired_date: date
    basis_type: str = Field(..., pattern=_BASIS_TYPE_PATTERN)
    asset_class: str | None = Field(default=None, pattern=_ASSET_CLASS_PATTERN)


class InvestmentLotUpdate(BaseModel):
    ticker: str | None = Field(default=None, min_length=1, max_length=16)
    shares: Decimal | None = Field(default=None, gt=0)
    basis_per_share: Decimal | None = Field(default=None, ge=0)
    acquired_date: date | None = None
    basis_type: str | None = Field(default=None, pattern=_BASIS_TYPE_PATTERN)
    asset_class: str | None = Field(default=None, pattern=_ASSET_CLASS_PATTERN)


class InvestmentLotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    ticker: str
    shares: Decimal
    basis_per_share: Decimal
    acquired_date: date
    basis_type: str
    asset_class: str | None
    created_at: datetime


class PositionRollup(BaseModel):
    """A holding aggregated across all visible lots for one ticker."""

    ticker: str
    shares: Decimal
    cost_basis: Decimal
    lot_count: int


class HoldingsMixSlice(BaseModel):
    asset_class: str  # "unclassified" for lots with no asset_class set
    cost_basis: Decimal
    percentage: float


class PositionsSummary(BaseModel):
    """Rollup of cost-basis lots for the Investments page: a ranked positions
    table and an asset-class mix. Cost basis is used (HearthLedger tracks no
    live market prices), so there is no market-value column."""

    positions: list[PositionRollup]
    holdings_mix: list[HoldingsMixSlice]
    total_cost_basis: Decimal
