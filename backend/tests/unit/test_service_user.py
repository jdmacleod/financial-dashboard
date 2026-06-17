import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user import UserService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id, member_id=member.id, role=role, household_id=household.id
    )


async def test_create_rejects_duplicate_email(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    other_member = await make_member(role="partner", display_name="Other")
    service = UserService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.create(
            ctx,
            UserCreate(
                member_id=other_member.id, email=primary_user.email, password="Whatever123!"
            ),
        )
    assert exc_info.value.status_code == 409


async def test_create_rejected_for_non_primary(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
    make_member: object,
) -> None:
    partner_member = await make_member(role="partner")
    service = UserService(db_session)
    ctx = _ctx(household, partner_member, "partner", primary_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.create(
            ctx,
            UserCreate(
                member_id=partner_member.id, email="new@example.com", password="Whatever123!"
            ),
        )
    assert exc_info.value.status_code == 403


async def test_update_rejected_for_non_primary_updating_other_user(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other_member = await make_member(role="partner", display_name="Other")
    other_user = await make_user(other_member, "other-target@example.com")

    service = UserService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, other_user.id, UserUpdate(email="new@example.com"))
    assert exc_info.value.status_code == 403


async def test_user_can_update_own_email(
    db_session: AsyncSession,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")

    service = UserService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    updated = await service.update(ctx, partner_user.id, UserUpdate(email="newemail@example.com"))
    assert updated.email == "newemail@example.com"


async def test_user_cannot_update_own_is_active(
    db_session: AsyncSession,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")

    service = UserService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(ctx, partner_user.id, UserUpdate(is_active=False))
    assert exc_info.value.status_code == 403


async def test_deactivate_clears_refresh_token_hash(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    target_member = await make_member(role="partner")
    target_user = await make_user(target_member, "target@example.com")
    target_user.refresh_token_hash = "some-hash"  # noqa: S105 — test fixture value, not a real secret
    await db_session.flush()

    service = UserService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    deactivated = await service.deactivate(ctx, target_user.id)
    assert deactivated.is_active is False
    assert deactivated.refresh_token_hash is None


async def test_deactivate_rejected_for_non_primary(
    db_session: AsyncSession,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    target_member = await make_member(role="partner", display_name="Target")
    target_user = await make_user(target_member, "target2@example.com")

    service = UserService(db_session)
    ctx = _ctx(household, partner_member, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.deactivate(ctx, target_user.id)
    assert exc_info.value.status_code == 403
