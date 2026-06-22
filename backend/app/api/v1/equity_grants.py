import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.equity_grant import EquityGrantResponse
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
