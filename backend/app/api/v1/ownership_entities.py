import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.ownership_entity import (
    OwnershipEntityCreate,
    OwnershipEntityResponse,
    OwnershipEntityUpdate,
)
from app.services.ownership_entity import OwnershipEntityService

router = APIRouter()


@router.get("/ownership-entities", response_model=list[OwnershipEntityResponse])
async def list_ownership_entities(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[OwnershipEntityResponse]:
    svc = OwnershipEntityService(session)
    return await svc.list_entities(ctx)


@router.post(
    "/ownership-entities",
    response_model=OwnershipEntityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ownership_entity(
    data: OwnershipEntityCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> OwnershipEntityResponse:
    svc = OwnershipEntityService(session)
    entity = await svc.create(ctx, data)
    return svc.to_response(entity)


@router.patch("/ownership-entities/{entity_id}", response_model=OwnershipEntityResponse)
async def update_ownership_entity(
    entity_id: uuid.UUID,
    data: OwnershipEntityUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> OwnershipEntityResponse:
    svc = OwnershipEntityService(session)
    entity = await svc.update(ctx, entity_id, data)
    return svc.to_response(entity)


@router.delete("/ownership-entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ownership_entity(
    entity_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = OwnershipEntityService(session)
    await svc.delete(ctx, entity_id)
