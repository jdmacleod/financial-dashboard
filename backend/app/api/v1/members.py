import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.db.models.member import HouseholdMember
from app.schemas.member import DashboardLayoutUpdate, MemberCreate, MemberResponse, MemberUpdate
from app.services.member import MemberService

router = APIRouter()


@router.get("/members", response_model=list[MemberResponse])
async def list_members(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[HouseholdMember]:
    svc = MemberService(session)
    return await svc.list_members(ctx)


@router.post("/members", response_model=MemberResponse, status_code=201)
async def create_member(
    data: MemberCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> HouseholdMember:
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
) -> HouseholdMember:
    svc = MemberService(session)
    return await svc.get_by_id(ctx, member_id)


@router.patch("/members/{member_id}", response_model=MemberResponse)
async def update_member(
    member_id: uuid.UUID,
    data: MemberUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> HouseholdMember:
    svc = MemberService(session)
    member = await svc.update(ctx, member_id, data)
    await session.commit()
    await session.refresh(member)
    return member


@router.patch("/members/{member_id}/dashboard-layout", response_model=MemberResponse)
async def update_dashboard_layout(
    member_id: uuid.UUID,
    data: DashboardLayoutUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> HouseholdMember:
    from fastapi import HTTPException, status
    from sqlalchemy import select

    result = await session.execute(select(HouseholdMember).where(HouseholdMember.id == member_id))
    member = result.scalar_one_or_none()
    if member is None or member.household_id != ctx.household_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if member.id != ctx.member_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Members may only update their own dashboard layout",
        )
    member.settings = {
        **member.settings,
        "dashboard_widgets": [w.model_dump() for w in data.widgets],
    }
    await session.commit()
    await session.refresh(member)
    return member


@router.delete("/members/{member_id}", status_code=204)
async def deactivate_member(
    member_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = MemberService(session)
    await svc.deactivate(ctx, member_id)
    await session.commit()
