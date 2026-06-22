import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.equity_grant import (
    EquityGrantCreate,
    EquityGrantResponse,
    EquityGrantUpdate,
)
from app.services.equity_comp import EquityCompService

router = APIRouter()


@router.get("/equity-grants", response_model=list[EquityGrantResponse])
async def list_equity_grants(
    member_id: uuid.UUID | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[EquityGrantResponse]:
    svc = EquityCompService(session)
    return await svc.list_grants(ctx, member_id=member_id)


@router.post(
    "/equity-grants",
    response_model=EquityGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_equity_grant(
    data: EquityGrantCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> EquityGrantResponse:
    svc = EquityCompService(session)
    grant = await svc.create_grant(ctx, data)
    return await svc.grant_response(ctx, grant)


@router.patch("/equity-grants/{grant_id}", response_model=EquityGrantResponse)
async def update_equity_grant(
    grant_id: uuid.UUID,
    data: EquityGrantUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> EquityGrantResponse:
    svc = EquityCompService(session)
    grant = await svc.update_grant(ctx, grant_id, data)
    return await svc.grant_response(ctx, grant)


@router.delete("/equity-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equity_grant(
    grant_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = EquityCompService(session)
    await svc.delete_grant(ctx, grant_id)
