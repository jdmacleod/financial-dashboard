from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.fire import DebtPayoffComparisonResponse
from app.services.debt_service import DebtService

router = APIRouter()


@router.get("/debt-payoff", response_model=DebtPayoffComparisonResponse)
async def get_debt_payoff(
    extra_monthly_payment: Decimal = Query(default=Decimal(0), ge=0),
    strategy: str | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> DebtPayoffComparisonResponse:
    svc = DebtService(session)
    return await svc.get_payoff_comparison(ctx, extra_monthly_payment=extra_monthly_payment)
