import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.db.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter()


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not ctx.is_primary:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    svc = UserService(session)
    user = await svc.create(data)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> User:
    svc = UserService(session)
    user = await svc.update(user_id, data, ctx.user_id, ctx.is_primary)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(
    user_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = UserService(session)
    await svc.deactivate(user_id, ctx.is_primary)
    await session.commit()
