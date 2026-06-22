from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.ownership_entity import OwnershipEntityResponse
from app.services.ownership_entity import OwnershipEntityService

router = APIRouter()


@router.get("/ownership-entities", response_model=list[OwnershipEntityResponse])
async def list_ownership_entities(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[OwnershipEntityResponse]:
    svc = OwnershipEntityService(session)
    return await svc.list_entities(ctx)
