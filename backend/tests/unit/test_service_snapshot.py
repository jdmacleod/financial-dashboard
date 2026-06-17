from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.account import AccountCreate, AccountType
from app.schemas.snapshot import SnapshotCreate, SnapshotUpdate
from app.services.account import AccountService
from app.services.snapshot import SnapshotService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


async def _make_account(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    account_type: AccountType = "checking",
    nickname: str = "Test Account",
) -> Any:
    svc = AccountService(db_session)
    return await svc.create(
        ctx,
        AccountCreate(account_type=account_type, nickname=nickname),
    )


async def test_list_snapshots(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = SnapshotService(db_session)
    await svc.create(
        ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 1, 31), balance=Decimal("5000.00")),
    )

    snapshots = await svc.list_snapshots(ctx, account.id)
    assert len(snapshots) >= 1
    assert any(s.balance == Decimal("5000.00") for s in snapshots)


async def test_create_snapshot_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, primary_ctx)

    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    svc = SnapshotService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            dep_ctx,
            account.id,
            SnapshotCreate(snapshot_date=date(2025, 1, 31), balance=Decimal("1000.00")),
        )
    assert exc_info.value.status_code == 403


async def test_create_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="savings", nickname="Savings")

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 1, 31), balance=Decimal("5000.00")),
    )

    assert snapshot.id is not None
    assert snapshot.account_id == account.id
    assert snapshot.balance == Decimal("5000.00")
    assert snapshot.snapshot_date == date(2025, 1, 31)
    assert snapshot.source == "manual"


async def test_update_snapshot_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, primary_ctx)

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        primary_ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 2, 28), balance=Decimal("3000.00")),
    )

    dep_member = await make_member(role="dependent", display_name="Dep2")
    dep_user = await make_user(dep_member, "dep2@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(
            dep_ctx,
            account.id,
            snapshot.id,
            SnapshotUpdate(balance=Decimal("9999.00")),
        )
    assert exc_info.value.status_code == 403


async def test_update_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(
        db_session, ctx, account_type="investment_brokerage", nickname="Brokerage"
    )

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 3, 31), balance=Decimal("10000.00")),
    )

    updated = await svc.update(
        ctx,
        account.id,
        snapshot.id,
        SnapshotUpdate(balance=Decimal("10500.00")),
    )
    assert updated.balance == Decimal("10500.00")
    assert updated.id == snapshot.id


async def test_get_snapshot_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = SnapshotService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, account.id, uuid.uuid4(), SnapshotUpdate(balance=Decimal("1.00")))
    assert exc_info.value.status_code == 404


async def test_delete_snapshot_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, primary_ctx)

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        primary_ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 4, 30), balance=Decimal("2000.00")),
    )

    dep_member = await make_member(role="dependent", display_name="Dep3")
    dep_user = await make_user(dep_member, "dep3@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(dep_ctx, account.id, snapshot.id)
    assert exc_info.value.status_code == 403


async def test_delete_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="retirement_401k", nickname="401k")

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 5, 31), balance=Decimal("50000.00")),
    )

    await svc.delete(ctx, account.id, snapshot.id)

    snapshots = await svc.list_snapshots(ctx, account.id)
    assert not any(s.id == snapshot.id for s in snapshots)


async def test_create_snapshot_with_optional_fields(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(
        db_session, ctx, account_type="retirement_roth_ira", nickname="Roth IRA"
    )

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        ctx,
        account.id,
        SnapshotCreate(
            snapshot_date=date(2025, 6, 30),
            balance=Decimal("15000.00"),
            contributed_ytd=Decimal("3000.00"),
            employer_match_ytd=Decimal("1500.00"),
            memo="Mid-year check",
        ),
    )

    assert snapshot.contributed_ytd == Decimal("3000.00")
    assert snapshot.employer_match_ytd == Decimal("1500.00")
    assert snapshot.memo == "Mid-year check"


async def test_update_snapshot_memo(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = SnapshotService(db_session)
    snapshot = await svc.create(
        ctx,
        account.id,
        SnapshotCreate(snapshot_date=date(2025, 7, 31), balance=Decimal("7500.00")),
    )

    updated = await svc.update(
        ctx,
        account.id,
        snapshot.id,
        SnapshotUpdate(memo="Updated memo"),
    )
    assert updated.memo == "Updated memo"
