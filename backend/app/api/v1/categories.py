import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category import CategoryService

router = APIRouter()


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryResponse]:
    svc = CategoryService(session)
    categories = await svc.list_categories(ctx)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CategoryResponse:
    svc = CategoryService(session)
    category = await svc.create(ctx, data)
    await session.commit()
    await session.refresh(category)
    return CategoryResponse.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CategoryResponse:
    svc = CategoryService(session)
    category = await svc.update(ctx, category_id, data)
    await session.commit()
    await session.refresh(category)
    return CategoryResponse.model_validate(category)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = CategoryService(session)
    await svc.delete(ctx, category_id)
    await session.commit()
