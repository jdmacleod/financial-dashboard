import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.investment_lot import (
    InvestmentLotCreate,
    InvestmentLotResponse,
    InvestmentLotUpdate,
    PositionsSummary,
)
from app.services.investment_lot import InvestmentLotService

router = APIRouter()


@router.get("/investment-positions", response_model=PositionsSummary)
async def get_investment_positions(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PositionsSummary:
    """Per-ticker positions and asset-class mix rolled up from cost-basis lots."""
    svc = InvestmentLotService(session)
    return await svc.positions_summary(ctx)


@router.get("/investment-lots", response_model=list[InvestmentLotResponse])
async def list_investment_lots(
    account_id: uuid.UUID | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[InvestmentLotResponse]:
    svc = InvestmentLotService(session)
    lots = await svc.list_lots(ctx, account_id=account_id)
    return [InvestmentLotResponse.model_validate(lot) for lot in lots]


@router.post(
    "/investment-lots",
    response_model=InvestmentLotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_investment_lot(
    data: InvestmentLotCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> InvestmentLotResponse:
    svc = InvestmentLotService(session)
    lot = await svc.create(ctx, data)
    return InvestmentLotResponse.model_validate(lot)


@router.patch("/investment-lots/{lot_id}", response_model=InvestmentLotResponse)
async def update_investment_lot(
    lot_id: uuid.UUID,
    data: InvestmentLotUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> InvestmentLotResponse:
    svc = InvestmentLotService(session)
    lot = await svc.update(ctx, lot_id, data)
    return InvestmentLotResponse.model_validate(lot)


@router.delete("/investment-lots/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investment_lot(
    lot_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = InvestmentLotService(session)
    await svc.delete(ctx, lot_id)
