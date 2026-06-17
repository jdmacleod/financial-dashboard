from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.transaction import TransactionCreate
from app.services.account import AccountService
from app.services.audit import AuditLogService
from app.services.transaction import TransactionService


def _ctx(
    household: Household,
    member: HouseholdMember,
    user: User,
    role: str = "primary",
) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


def _now() -> datetime:
    return datetime.now(UTC)


async def _make_account(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    nickname: str = "Test Account",
    account_type: str = "checking",
) -> Account:
    return await AccountService(db_session).create(
        ctx,
        AccountCreate(account_type=account_type, nickname=nickname),  # type: ignore[arg-type]
    )


async def _make_transaction(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    account_id: uuid.UUID,
    txn_date: date | None = None,
    amount: Decimal | None = None,
) -> Transaction:
    return await TransactionService(db_session).create(
        ctx,
        account_id,
        TransactionCreate(
            transaction_date=txn_date or date(2025, 1, 1),
            amount=amount or Decimal("-50"),
        ),
    )


# ---------------------------------------------------------------------------
# Basic list tests
# ---------------------------------------------------------------------------


async def test_list_entries_basic(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    result = await svc.list_entries(ctx)

    assert result.total > 0
    assert len(result.items) > 0


async def test_list_entries_user_id_filter(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    result = await svc.list_entries(ctx, user_id=primary_user.id)

    assert result.total > 0
    for item in result.items:
        assert item.user_id == primary_user.id


async def test_list_entries_member_id_filter(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    result = await svc.list_entries(ctx, member_id=primary_member.id)

    assert result.total > 0


async def test_list_entries_date_filters(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    now = datetime.now(UTC)
    # Date filter that includes entries
    result_in = await svc.list_entries(
        ctx,
        from_date=now - timedelta(minutes=5),
        to_date=now + timedelta(minutes=5),
    )
    assert result_in.total > 0

    # Date filter that excludes all entries (future only)
    result_out = await svc.list_entries(
        ctx,
        from_date=now + timedelta(days=365),
        to_date=now + timedelta(days=366),
    )
    assert result_out.total == 0


async def test_list_entries_entity_type_filter(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    txn = await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    result = await svc.list_entries(ctx, entity_type="transaction", entity_id=txn.id)

    assert result.total >= 1
    for item in result.items:
        assert item.entity_type == "transaction"
        assert item.entity_id == txn.id
    # When entity_id is provided, ordering should be ascending (record history)
    if len(result.items) > 1:
        assert result.items[0].created_at <= result.items[-1].created_at


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


async def test_list_entries_forbidden_for_non_primary_general_feed(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    dep_member: HouseholdMember = await make_member(role="dependent", display_name="Dep")
    dep_user: User = await make_user(dep_member, "dep@example.com")
    dep_ctx = _ctx(household, dep_member, dep_user, "dependent")

    svc = AuditLogService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.list_entries(dep_ctx)
    assert exc_info.value.status_code == 403


async def test_list_entries_partner_can_view_own_transaction_history(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    partner_member: HouseholdMember = await make_member(role="partner", display_name="Partner")
    partner_user: User = await make_user(partner_member, "partner@example.com")
    primary_ctx = _ctx(household, primary_member, primary_user)
    partner_ctx = _ctx(household, partner_member, partner_user, "partner")

    # Create a joint account (no owner) and a transaction using the primary ctx
    account = await _make_account(db_session, primary_ctx, "Joint Checking")
    txn = await _make_transaction(db_session, primary_ctx, account.id)

    svc = AuditLogService(db_session)
    # Partner can view audit history of a transaction on a visible account
    result = await svc.list_entries(partner_ctx, entity_type="transaction", entity_id=txn.id)
    assert result.total >= 1


async def test_list_entries_partner_forbidden_for_member_entity_type(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    partner_member: HouseholdMember = await make_member(role="partner", display_name="Partner2")
    partner_user: User = await make_user(partner_member, "partner2@example.com")
    partner_ctx = _ctx(household, partner_member, partner_user, "partner")

    svc = AuditLogService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.list_entries(partner_ctx, entity_type="member", entity_id=primary_member.id)
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Enrich batch / display name test
# ---------------------------------------------------------------------------


async def test_enrich_batch_populates_display_name(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)
    await _make_transaction(db_session, ctx, account.id)

    svc = AuditLogService(db_session)
    result = await svc.list_entries(ctx)

    assert result.total > 0
    # At least one entry should have a user_display_name populated
    entries_with_user = [i for i in result.items if i.user_id == primary_user.id]
    assert len(entries_with_user) > 0
    for entry in entries_with_user:
        assert entry.user_display_name is not None
        assert len(entry.user_display_name) > 0


# ---------------------------------------------------------------------------
# Pagination test
# ---------------------------------------------------------------------------


async def test_list_entries_pagination(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx)

    # Create 3 transactions → at least 3 audit entries (plus the account.created entry)
    await _make_transaction(db_session, ctx, account.id, date(2025, 1, 1), Decimal("-10"))
    await _make_transaction(db_session, ctx, account.id, date(2025, 1, 2), Decimal("-20"))
    await _make_transaction(db_session, ctx, account.id, date(2025, 1, 3), Decimal("-30"))

    svc = AuditLogService(db_session)
    page1 = await svc.list_entries(ctx, page=1, page_size=2)
    page2 = await svc.list_entries(ctx, page=2, page_size=2)

    assert page1.total >= 4  # 1 account + 3 transactions
    assert len(page1.items) == 2
    assert page1.page == 1

    # Page 2 should have different items than page 1
    page1_ids = {item.id for item in page1.items}
    page2_ids = {item.id for item in page2.items}
    assert page1_ids.isdisjoint(page2_ids)
    assert page2.page == 2
