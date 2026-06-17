import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS
from app.core.visibility import VisibilityContext
from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.account import AccessGrantCreate, AccountCreate, AccountUpdate
from app.services.account import AccountService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id, member_id=member.id, role=role, household_id=household.id
    )


async def _latest_audit_row(db_session: AsyncSession, action: str) -> AuditLog:
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )
    return result.scalars().first()


def _assert_no_excluded_fields(row: AuditLog) -> None:
    for field in AUDIT_EXCLUDED_FIELDS:
        assert field not in (row.previous_value or {})
        assert field not in (row.new_value or {})


async def test_create_audit_row_excludes_pii(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    await service.create(
        ctx,
        AccountCreate(
            account_type="checking",
            nickname="Chase Checking",
            institution_name="Chase Bank",
            account_number="1234567890",
            routing_number="021000021",
        ),
    )
    row = await _latest_audit_row(db_session, "account.created")
    _assert_no_excluded_fields(row)


async def test_update_audit_row_excludes_pii_even_when_unchanged(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(
            account_type="checking",
            nickname="Chase Checking",
            institution_name="Chase Bank",
            account_number="1234567890",
        ),
    )
    await service.update(ctx, account.id, AccountUpdate(nickname="Renamed Checking"))
    row = await _latest_audit_row(db_session, "account.updated")
    _assert_no_excluded_fields(row)
    assert row.new_value["nickname"] == "Renamed Checking"


async def test_deactivate_audit_row_excludes_pii(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(account_type="checking", nickname="Chase", institution_name="Chase Bank"),
    )
    await service.deactivate(ctx, account.id)
    row = await _latest_audit_row(db_session, "account.deactivated")
    _assert_no_excluded_fields(row)


async def test_non_owner_partner_cannot_update_another_members_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner = await make_member(role="partner", display_name="Owner")
    other_partner = await make_member(role="partner", display_name="Other")
    other_user = await make_user(other_partner, "other@example.com")

    service = AccountService(db_session)
    owner_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        owner_ctx,
        AccountCreate(account_type="checking", nickname="Owner Checking", owner_member_id=owner.id),
    )

    other_ctx = _ctx(household, other_partner, "partner", other_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(other_ctx, account.id, AccountUpdate(nickname="Hacked"))
    assert exc_info.value.status_code in (403, 404)


async def test_create_grant_rejects_joint_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    grantee = await make_member(role="partner")
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Joint Checking")
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id))
    assert exc_info.value.status_code == 400


async def test_create_grant_rejects_self_grant_to_owner(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    owner = await make_member(role="partner")
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id),
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(ctx, account.id, AccessGrantCreate(grantee_member_id=owner.id))
    assert exc_info.value.status_code == 400


async def test_create_grant_rejected_for_non_primary(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner = await make_member(role="partner")
    grantee = await make_member(role="partner", display_name="Grantee")
    partner_user = await make_user(owner, "owner@example.com")

    service = AccountService(db_session)
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        primary_ctx,
        AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id),
    )

    partner_ctx = _ctx(household, owner, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(
            partner_ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id)
        )
    assert exc_info.value.status_code == 403


async def test_create_and_revoke_grant_happy_path(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    owner = await make_member(role="partner")
    grantee = await make_member(role="partner", display_name="Grantee")

    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id)
    )
    grant = await service.create_grant(
        ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id)
    )
    assert grant.is_active is True

    await service.revoke_grant(ctx, account.id, grant.id)
    grants = await service.list_grants(ctx, account.id)
    assert all(g.id != grant.id for g in grants)
