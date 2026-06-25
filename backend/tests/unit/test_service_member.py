import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.member import MemberCreate, MemberUpdate
from app.services.member import MemberService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id, member_id=member.id, role=role, household_id=household.id
    )


async def test_cannot_deactivate_sole_remaining_primary(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = MemberService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.deactivate(ctx, primary_member.id)
    assert exc_info.value.status_code == 409


async def test_cannot_demote_sole_remaining_primary(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = MemberService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, primary_member.id, MemberUpdate(role="partner"))
    assert exc_info.value.status_code == 409


async def test_can_deactivate_primary_when_another_primary_remains(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    second_primary = await make_member(role="primary", display_name="Second Primary")
    service = MemberService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    deactivated = await service.deactivate(ctx, primary_member.id)
    assert deactivated.is_active is False
    others = await service.get_by_id(ctx, second_primary.id)
    assert others.is_active is True


async def test_create_rejected_for_non_primary(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.create(ctx, MemberCreate(display_name="New Member"))
    assert exc_info.value.status_code == 403


async def test_update_other_member_rejected_for_non_primary(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other_member = await make_member(role="partner", display_name="Other")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, other_member.id, MemberUpdate(display_name="Renamed"))
    assert exc_info.value.status_code == 403


async def test_update_self_allowed_for_non_primary(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    from datetime import date

    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    updated = await service.update(
        ctx,
        partner_member.id,
        MemberUpdate(display_name="Renamed Self", date_of_birth=date(1985, 3, 1)),
    )
    assert updated.display_name == "Renamed Self"
    assert updated.date_of_birth == date(1985, 3, 1)


async def test_self_cannot_change_own_role(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, partner_member.id, MemberUpdate(role="primary"))
    assert exc_info.value.status_code == 403


async def test_self_cannot_change_own_activation(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, partner_member.id, MemberUpdate(is_active=False))
    assert exc_info.value.status_code == 403


async def test_deactivate_rejected_for_non_primary(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other_member = await make_member(role="partner", display_name="Other")
    service = MemberService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.deactivate(ctx, other_member.id)
    assert exc_info.value.status_code == 403
