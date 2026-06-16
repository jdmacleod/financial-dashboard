import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.member import MemberCreate, MemberResponse, MemberUpdate
from app.services.member import MemberService

router = APIRouter()


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = MemberService(session)
    return await svc.list(ctx)


@router.post("/members", response_model=MemberResponse, status_code=201)
async def create_member(
    data: MemberCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = MemberService(session)
    member = await svc.create(ctx, data)
    await session.commit()
    await session.refresh(member)
    return member


@router.get("/members/{member_id}", response_model=MemberResponse)
async def get_member(
    member_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = MemberService(session)
    return await svc.get_by_id(ctx, member_id)


@router.patch("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: uuid.UUID,
    data: MemberUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = MemberService(session)
    member = await svc.update(ctx, member_id, data)
    await session.commit()
    await session.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=204)
async def deactivate_member(
    member_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
):
    svc = MemberService(session)
    await svc.deactivate(ctx, member_id)
    await session.commit()
