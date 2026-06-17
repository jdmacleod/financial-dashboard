from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import Account
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.repositories.account import AccountRepository


async def _make_account(
    db_session: AsyncSession, household: Household, owner_member_id: object = None
) -> Account:
    now = datetime.now(UTC)
    account = Account(
        household_id=household.id,
        owner_member_id=owner_member_id,
        account_type="checking",
        nickname="Account",
        include_in_net_worth=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(account)
    await db_session.flush()
    return account


def _ctx(household: Household, member: HouseholdMember, role: str) -> VisibilityContext:
    return VisibilityContext(
        user_id=member.id, member_id=member.id, role=role, household_id=household.id
    )


async def test_primary_sees_all_household_accounts(
    db_session: AsyncSession, household: Household, make_member: object
) -> None:
    primary = await make_member(role="primary")
    other = await make_member(role="partner", display_name="Other")
    joint = await _make_account(db_session, household, owner_member_id=None)
    owned_by_other = await _make_account(db_session, household, owner_member_id=other.id)

    repo = AccountRepository(db_session)
    visible = await repo.get_visible(_ctx(household, primary, "primary"))
    visible_ids = {a.id for a in visible}
    assert joint.id in visible_ids
    assert owned_by_other.id in visible_ids


async def test_partner_sees_only_owned_and_joint_accounts(
    db_session: AsyncSession, household: Household, make_member: object
) -> None:
    partner = await make_member(role="partner")
    other = await make_member(role="partner", display_name="Other")
    own = await _make_account(db_session, household, owner_member_id=partner.id)
    joint = await _make_account(db_session, household, owner_member_id=None)
    others = await _make_account(db_session, household, owner_member_id=other.id)

    repo = AccountRepository(db_session)
    visible_ids = {a.id for a in await repo.get_visible(_ctx(household, partner, "partner"))}
    assert own.id in visible_ids
    assert joint.id in visible_ids
    assert others.id not in visible_ids


async def test_partner_sees_account_with_active_grant(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner = await make_member(role="partner")
    other = await make_member(role="partner", display_name="Other")
    other_user = await make_user(other, "other@example.com")
    granted = await _make_account(db_session, household, owner_member_id=other.id)

    grant = AccountAccessGrant(
        account_id=granted.id,
        owner_member_id=other.id,
        grantee_member_id=partner.id,
        granted_by_user_id=other_user.id,
        access_level="read",
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(grant)
    await db_session.flush()

    repo = AccountRepository(db_session)
    visible_ids = {a.id for a in await repo.get_visible(_ctx(household, partner, "partner"))}
    assert granted.id in visible_ids


async def test_partner_does_not_see_account_with_revoked_grant(
    db_session: AsyncSession, household: Household, make_member: object, make_user: object
) -> None:
    partner = await make_member(role="partner")
    other = await make_member(role="partner", display_name="Other")
    other_user = await make_user(other, "other2@example.com")
    granted = await _make_account(db_session, household, owner_member_id=other.id)

    grant = AccountAccessGrant(
        account_id=granted.id,
        owner_member_id=other.id,
        grantee_member_id=partner.id,
        granted_by_user_id=other_user.id,
        access_level="read",
        is_active=False,
        revoked_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    db_session.add(grant)
    await db_session.flush()

    repo = AccountRepository(db_session)
    visible_ids = {a.id for a in await repo.get_visible(_ctx(household, partner, "partner"))}
    assert granted.id not in visible_ids


async def test_dependent_sees_only_own_accounts(
    db_session: AsyncSession, household: Household, make_member: object
) -> None:
    dependent = await make_member(role="dependent")
    other = await make_member(role="partner", display_name="Other")
    own = await _make_account(db_session, household, owner_member_id=dependent.id)
    others = await _make_account(db_session, household, owner_member_id=other.id)
    joint = await _make_account(db_session, household, owner_member_id=None)

    repo = AccountRepository(db_session)
    visible_ids = {a.id for a in await repo.get_visible(_ctx(household, dependent, "dependent"))}
    assert own.id in visible_ids
    assert joint.id in visible_ids
    assert others.id not in visible_ids


async def test_get_by_id_raises_404_for_invisible_account(
    db_session: AsyncSession, household: Household, make_member: object
) -> None:
    dependent = await make_member(role="dependent")
    other = await make_member(role="partner", display_name="Other")
    others_account = await _make_account(db_session, household, owner_member_id=other.id)

    repo = AccountRepository(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await repo.get_by_id(_ctx(household, dependent, "dependent"), others_account.id)
    assert exc_info.value.status_code == 404


async def test_get_by_id_returns_visible_account(
    db_session: AsyncSession, household: Household, make_member: object
) -> None:
    primary = await make_member(role="primary")
    account = await _make_account(db_session, household, owner_member_id=None)

    repo = AccountRepository(db_session)
    found = await repo.get_by_id(_ctx(household, primary, "primary"), account.id)
    assert found.id == account.id
