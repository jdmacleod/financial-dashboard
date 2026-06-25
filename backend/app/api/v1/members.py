import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.db.models.member import HouseholdMember
from app.schemas.member import DashboardLayoutUpdate, MemberCreate, MemberResponse, MemberUpdate
from app.schemas.provisioning import (
    ProvisionRequest,
    ProvisionResponse,
    TemporaryPasswordResponse,
)
from app.schemas.social_security import SocialSecurityComparison
from app.schemas.user import UserResponse
from app.services.member import MemberService
from app.services.provisioning import ProvisionService
from app.services.social_security import claiming_comparison

router = APIRouter()


@router.post(
    "/members/provision",
    response_model=ProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_member(
    data: ProvisionRequest,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> ProvisionResponse:
    """Add a login-capable member in one action. Primary/partner only; only a
    primary may provision another primary. Returns the temporary password once.
    """
    svc = ProvisionService(session)
    result = await svc.provision(ctx, data)
    await session.commit()
    await session.refresh(result.member)
    await session.refresh(result.user)
    return ProvisionResponse(
        member=MemberResponse.model_validate(result.member),
        user=UserResponse.model_validate(result.user),
        temporary_password=result.temporary_password,
    )


@router.post(
    "/members/users/{user_id}/temporary-password",
    response_model=TemporaryPasswordResponse,
)
async def regenerate_temporary_password(
    user_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> TemporaryPasswordResponse:
    """Re-issue a temporary password for a not-yet-claimed provisioned user."""
    svc = ProvisionService(session)
    temporary_password = await svc.regenerate_temporary_password(ctx, user_id)
    await session.commit()
    return TemporaryPasswordResponse(temporary_password=temporary_password)


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


@router.get(
    "/members/{member_id}/social-security-estimate",
    response_model=SocialSecurityComparison,
)
async def social_security_estimate(
    member_id: uuid.UUID,
    monthly_benefit_at_fra: Decimal = Query(ge=0, description="Estimated monthly benefit at FRA"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> SocialSecurityComparison:
    """Adjusted Social Security benefit by claiming age (62-70) for this member.

    `monthly_benefit_at_fra` is the member's PIA estimate (e.g. from the SSA
    statement); the member's date of birth determines Full Retirement Age.
    """
    svc = MemberService(session)
    member = await svc.get_by_id(ctx, member_id)
    if member.date_of_birth is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member has no date of birth; required to compute Full Retirement Age.",
        )
    return claiming_comparison(monthly_benefit_at_fra, member.date_of_birth)


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
