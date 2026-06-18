from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.account import AccountCreate, AccountType
from app.schemas.transaction import BulkCategorizeRequest, TransactionCreate, TransactionUpdate
from app.services.account import AccountService
from app.services.transaction import TransactionService


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
    nickname: str = "Test Checking",
    owner_member_id: uuid.UUID | None = None,
) -> Any:
    svc = AccountService(db_session)
    return await svc.create(
        ctx,
        AccountCreate(
            account_type=account_type,
            nickname=nickname,
            owner_member_id=owner_member_id,
        ),
    )


async def _make_category(db_session: AsyncSession, household: Household) -> Category:
    cat = Category(
        household_id=household.id,
        name="Groceries",
        is_income=False,
        is_system=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


async def test_create_transaction(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            payee_normalized="Store",
        ),
    )

    assert txn.id is not None
    assert txn.account_id == account.id
    assert txn.amount == Decimal("-50.00")
    assert txn.payee_normalized == "Store"
    assert txn.source == "manual"


async def test_get_transaction(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    created = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 2, 15),
            amount=Decimal("-25.00"),
            payee_normalized="Coffee Shop",
        ),
    )

    fetched = await svc.get(ctx, created.id)
    assert fetched.id == created.id
    assert fetched.payee_normalized == "Coffee Shop"


async def test_get_transaction_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = TransactionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_update_transaction_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    cat = await _make_category(db_session, household)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 3, 10),
            amount=Decimal("-100.00"),
            payee_normalized="Supermarket",
        ),
    )

    updated = await svc.update(ctx, txn.id, TransactionUpdate(category_id=cat.id))
    assert updated.category_id == cat.id
    assert updated.is_reviewed is True


async def test_update_transaction_amount(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 4, 1),
            amount=Decimal("-200.00"),
            payee_normalized="Electric Company",
        ),
    )

    updated = await svc.update(ctx, txn.id, TransactionUpdate(amount=Decimal("-210.00")))
    assert updated.amount == Decimal("-210.00")


async def test_delete_transaction(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 5, 1),
            amount=Decimal("-75.00"),
            payee_normalized="Restaurant",
        ),
    )

    await svc.delete(ctx, txn.id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, txn.id)
    assert exc_info.value.status_code == 404


async def test_bulk_categorize(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    cat = await _make_category(db_session, household)

    svc = TransactionService(db_session)
    txn1 = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 6, 1),
            amount=Decimal("-30.00"),
            payee_normalized="Bakery",
        ),
    )
    txn2 = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 6, 2),
            amount=Decimal("-45.00"),
            payee_normalized="Deli",
        ),
    )

    updated = await svc.bulk_categorize(
        ctx,
        account.id,
        BulkCategorizeRequest(transaction_ids=[txn1.id, txn2.id], category_id=cat.id),
    )

    assert len(updated) == 2
    assert all(t.category_id == cat.id for t in updated)
    assert all(t.is_reviewed is True for t in updated)


async def test_create_transaction_forbidden_for_dependent(
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

    svc = TransactionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            dep_ctx,
            account.id,
            TransactionCreate(
                transaction_date=date(2025, 1, 1),
                amount=Decimal("-10.00"),
                payee_normalized="Forbidden",
            ),
        )
    assert exc_info.value.status_code == 403


async def test_create_transaction_forbidden_partner_private_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    """Partner should get 403 trying to create a transaction on primary's private account."""
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    # Create account owned by primary_member (private)
    account = await _make_account(db_session, primary_ctx, owner_member_id=primary_member.id)

    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    partner_ctx = VisibilityContext(
        user_id=partner_user.id,
        member_id=partner_member.id,
        role="partner",
        household_id=household.id,
    )

    svc = TransactionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            partner_ctx,
            account.id,
            TransactionCreate(
                transaction_date=date(2025, 1, 1),
                amount=Decimal("-10.00"),
                payee_normalized="Forbidden",
            ),
        )
    # AccountRepository.get_by_id hides inaccessible accounts as 404 (not 403)
    # to prevent resource enumeration — private accounts are invisible to partners
    assert exc_info.value.status_code == 404


async def test_list_for_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 7, 1),
            amount=Decimal("-55.00"),
            payee_normalized="Gas Station",
        ),
    )

    items, total = await svc.list_for_account(ctx, account.id)
    assert total >= 1
    assert any(t.payee_normalized == "Gas Station" for t in items)


async def test_update_transaction_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = TransactionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, uuid.uuid4(), TransactionUpdate(amount=Decimal("-99.00")))
    assert exc_info.value.status_code == 404


async def test_delete_transaction_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = TransactionService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_transaction_date(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 1, 15),
            amount=Decimal("-50.00"),
            payee_normalized="Grocery Store",
        ),
    )

    updated = await svc.update(ctx, txn.id, TransactionUpdate(transaction_date=date(2025, 2, 1)))
    assert updated.transaction_date == date(2025, 2, 1)


@pytest.mark.asyncio
async def test_update_transaction_memo(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = TransactionService(db_session)
    txn = await svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 1, 15),
            amount=Decimal("-50.00"),
            payee_normalized="Grocery Store",
            memo="Initial memo",
        ),
    )

    updated = await svc.update(ctx, txn.id, TransactionUpdate(memo="Updated memo"))
    assert updated.memo == "Updated memo"

    cleared = await svc.update(ctx, txn.id, TransactionUpdate(memo=None))
    assert cleared.memo is None
