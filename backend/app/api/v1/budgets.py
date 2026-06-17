import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.services.budget import BudgetService

router = APIRouter()


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    category_id: uuid.UUID | None = Query(None),
    effective_date: date | None = Query(None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[BudgetResponse]:
    svc = BudgetService(session)
    budgets = await svc.list_budgets(ctx, category_id=category_id, effective_date=effective_date)
    return [BudgetResponse.model_validate(b) for b in budgets]


@router.post("/budgets", response_model=BudgetResponse, status_code=201)
async def create_budget(
    data: BudgetCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> BudgetResponse:
    svc = BudgetService(session)
    budget = await svc.create(ctx, data)
    await session.commit()
    await session.refresh(budget)
    return BudgetResponse.model_validate(budget)


@router.patch("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> BudgetResponse:
    svc = BudgetService(session)
    budget = await svc.update(ctx, budget_id, data)
    await session.commit()
    await session.refresh(budget)
    return BudgetResponse.model_validate(budget)


@router.delete("/budgets/{budget_id}", status_code=204)
async def delete_budget(
    budget_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = BudgetService(session)
    await svc.delete(ctx, budget_id)
    await session.commit()
