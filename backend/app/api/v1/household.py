from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.db.models.household import Household
from app.schemas.household import HouseholdResponse, HouseholdUpdate

router = APIRouter()


@router.get("/household", response_model=HouseholdResponse)
async def get_household(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Household).where(Household.id == ctx.household_id))
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=404)
    return household


@router.patch("/household", response_model=HouseholdResponse)
async def update_household(
    data: HouseholdUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    if not ctx.is_primary:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = await session.execute(select(Household).where(Household.id == ctx.household_id))
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=404)
    if data.name is not None:
        household.name = data.name
    if data.settings is not None:
        household.settings = data.settings
    await session.commit()
    await session.refresh(household)
    return household
