from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionAccount
from app.db.models.user import User
from app.repositories.account import AccountRepository
from app.repositories.pension import PensionRepository
from app.schemas.account import AccountCreate
from app.services.account import AccountService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


async def _make_pension_account(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    is_vested: bool = True,
    monthly_benefit: Decimal | None = Decimal("2500.00"),
    owner_member_id: uuid.UUID | None = None,
    nickname: str = "My Pension",
) -> tuple:
    svc = AccountService(db_session)
    account = await svc.create(
        ctx,
        AccountCreate(
            account_type="pension",
            nickname=nickname,
            owner_member_id=owner_member_id,
        ),
    )
    now = datetime.now(UTC)
    pension = PensionAccount(
        account_id=account.id,
        is_vested=is_vested,
        monthly_benefit_estimate=monthly_benefit,
        cola_adjustment_rate=Decimal("0.02"),
        created_at=now,
        updated_at=now,
    )
    db_session.add(pension)
    await db_session.flush()
    await db_session.refresh(pension)
    return account, pension


async def test_get_by_account_id(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account, pension = await _make_pension_account(db_session, ctx)

    repo = PensionRepository(db_session)
    fetched = await repo.get_by_account_id(account.id)
    assert fetched is not None
    assert fetched.id == pension.id


async def test_get_by_account_id_not_found(
    db_session: AsyncSession,
) -> None:
    repo = PensionRepository(db_session)
    result = await repo.get_by_account_id(uuid.uuid4())
    assert result is None


async def test_get_by_account_ids(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    acc1, pen1 = await _make_pension_account(db_session, ctx, nickname="Pension A")
    acc2, pen2 = await _make_pension_account(db_session, ctx, nickname="Pension B")

    repo = PensionRepository(db_session)
    result = await repo.get_by_account_ids([acc1.id, acc2.id])
    assert len(result) == 2
    ids = {p.id for p in result}
    assert pen1.id in ids
    assert pen2.id in ids


async def test_get_by_account_ids_empty(
    db_session: AsyncSession,
) -> None:
    repo = PensionRepository(db_session)
    result = await repo.get_by_account_ids([])
    assert result == []


async def test_get_vested_by_household_only_visible(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    _, vested = await _make_pension_account(db_session, ctx, is_vested=True, nickname="Vested P")
    _, unvested = await _make_pension_account(
        db_session, ctx, is_vested=False, nickname="Unvested P"
    )

    repo = PensionRepository(db_session)
    results = await repo.get_vested_by_household(ctx)
    result_ids = {r[0].id for r in results}
    assert vested.id in result_ids
    assert unvested.id not in result_ids


async def test_get_vested_rbac_respects_visibility(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member,
    make_user,
) -> None:
    """Partner cannot see vested pensions on primary's private accounts."""
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)

    # Private account owned by primary
    _, private_pension = await _make_pension_account(
        db_session,
        primary_ctx,
        owner_member_id=primary_member.id,
        nickname="Primary Private Pension",
    )

    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    partner_ctx = VisibilityContext(
        user_id=partner_user.id,
        member_id=partner_member.id,
        role="partner",
        household_id=household.id,
    )

    repo = PensionRepository(db_session)
    results = await repo.get_vested_by_household(partner_ctx)
    result_ids = {r[0].id for r in results}
    assert private_pension.id not in result_ids


async def test_latest_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    from datetime import date

    from app.db.models.snapshot import AccountSnapshot

    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = AccountService(db_session)
    account = await svc.create(
        ctx,
        AccountCreate(account_type="checking", nickname="Checking"),
    )

    snap = AccountSnapshot(
        account_id=account.id,
        snapshot_date=date(2025, 12, 31),
        balance=Decimal("10000.00"),
        contributed_ytd=Decimal("0"),
        employer_match_ytd=Decimal("0"),
        source="manual",
        created_at=datetime.now(UTC),
    )
    db_session.add(snap)
    await db_session.flush()

    account_repo = AccountRepository(db_session)
    result = await account_repo.latest_snapshot(account.id)
    assert result is not None
    balance, snap_date = result
    assert balance == Decimal("10000.00")
    assert snap_date == date(2025, 12, 31)


async def test_latest_snapshot_none(
    db_session: AsyncSession,
) -> None:
    account_repo = AccountRepository(db_session)
    result = await account_repo.latest_snapshot(uuid.uuid4())
    assert result is None
