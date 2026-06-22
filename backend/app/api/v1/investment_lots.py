import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.investment_lot import InvestmentLotResponse
from app.services.investment_lot import InvestmentLotService

router = APIRouter()


@router.get("/investment-lots", response_model=list[InvestmentLotResponse])
async def list_investment_lots(
    account_id: uuid.UUID | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[InvestmentLotResponse]:
    svc = InvestmentLotService(session)
    lots = await svc.list_lots(ctx, account_id=account_id)
    return [InvestmentLotResponse.model_validate(lot) for lot in lots]
