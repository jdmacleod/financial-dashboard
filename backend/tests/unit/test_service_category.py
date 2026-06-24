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
from app.schemas.account import AccountCreate
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.transaction import TransactionCreate
from app.services.account import AccountService
from app.services.category import CategoryService
from app.services.transaction import TransactionService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


async def test_list_categories(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    await svc.create(ctx, CategoryCreate(name="Transport"))

    cats = await svc.list_categories(ctx)
    assert any(c.name == "Transport" for c in cats)


async def test_get_category_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, uuid.uuid4(), CategoryUpdate(name="Ghost"))
    assert exc_info.value.status_code in (403, 404)


async def test_create_category_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    svc = CategoryService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(dep_ctx, CategoryCreate(name="Forbidden"))
    assert exc_info.value.status_code == 403


async def test_create_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    cat = await svc.create(ctx, CategoryCreate(name="Food"))

    assert cat.id is not None
    assert cat.name == "Food"
    assert cat.household_id == household.id
    assert cat.is_system is False
    assert cat.is_income is False


async def test_update_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    cat = await svc.create(ctx, CategoryCreate(name="Old Name"))
    updated = await svc.update(ctx, cat.id, CategoryUpdate(name="New Name"))

    assert updated.name == "New Name"
    assert updated.id == cat.id


async def test_update_category_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)
    cat = await svc.create(primary_ctx, CategoryCreate(name="Some Category"))

    dep_member = await make_member(role="dependent", display_name="Dep2")
    dep_user = await make_user(dep_member, "dep2@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(dep_ctx, cat.id, CategoryUpdate(name="Hacked"))
    assert exc_info.value.status_code == 403


async def test_update_system_category_returns_409(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)

    sys_cat = Category(
        household_id=household.id,
        name="System Cat",
        is_income=False,
        is_system=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(sys_cat)
    await db_session.flush()

    svc = CategoryService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, sys_cat.id, CategoryUpdate(name="Renamed System"))
    assert exc_info.value.status_code == 409


async def test_delete_category_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)
    cat = await svc.create(primary_ctx, CategoryCreate(name="To Delete"))

    dep_member = await make_member(role="dependent", display_name="Dep3")
    dep_user = await make_user(dep_member, "dep3@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(dep_ctx, cat.id)
    assert exc_info.value.status_code == 403


async def test_delete_system_category_returns_409(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)

    sys_cat = Category(
        household_id=household.id,
        name="Uncategorized",
        is_income=False,
        is_system=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(sys_cat)
    await db_session.flush()

    svc = CategoryService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(ctx, sys_cat.id)
    assert exc_info.value.status_code == 409


async def test_delete_category_reassigns_to_uncategorized(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)

    # Create the "Uncategorized" system category
    uncategorized = Category(
        household_id=household.id,
        name="Uncategorized",
        is_income=False,
        is_system=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(uncategorized)
    await db_session.flush()

    # Create a custom category
    svc = CategoryService(db_session)
    custom_cat = await svc.create(ctx, CategoryCreate(name="Custom Category"))

    # Create an account and transaction linked to custom_cat
    acct_svc = AccountService(db_session)
    account = await acct_svc.create(
        ctx, AccountCreate(account_type="checking", nickname="Checking")
    )
    txn_svc = TransactionService(db_session)
    txn = await txn_svc.create(
        ctx,
        account.id,
        TransactionCreate(
            transaction_date=date(2025, 1, 15),
            amount=Decimal("-20.00"),
            payee_normalized="Some Store",
            category_id=custom_cat.id,
        ),
    )
    assert txn.category_id == custom_cat.id

    # Delete custom category — transaction should be reassigned to Uncategorized
    await svc.delete(ctx, custom_cat.id)

    # Reload transaction from DB
    from sqlalchemy import select

    from app.db.models.transaction import Transaction

    result = await db_session.execute(select(Transaction).where(Transaction.id == txn.id))
    reloaded = result.scalar_one()
    assert reloaded.category_id == uncategorized.id


async def test_delete_category_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_create_category_with_income_flag(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    cat = await svc.create(ctx, CategoryCreate(name="Salary", is_income=True))
    assert cat.is_income is True


def test_retirement_income_slugs_mapping() -> None:
    from app.services.report import RETIREMENT_INCOME_SLUGS

    assert "social_security_income" in RETIREMENT_INCOME_SLUGS
    assert "pension_income" in RETIREMENT_INCOME_SLUGS
    assert "rmd_distribution" in RETIREMENT_INCOME_SLUGS
    assert RETIREMENT_INCOME_SLUGS["social_security_income"] == "social_security"
    assert RETIREMENT_INCOME_SLUGS["pension_income"] == "pension"
    assert RETIREMENT_INCOME_SLUGS["rmd_distribution"] == "rmd"


@pytest.mark.asyncio
async def test_update_system_category_color_hex_allowed(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    system_cat = await svc.create(ctx, CategoryCreate(name="System Test", is_income=False))
    system_cat.is_system = True
    await db_session.flush()

    updated = await svc.update(ctx, system_cat.id, CategoryUpdate(color_hex="#ff0000"))
    assert updated.color_hex == "#ff0000"


@pytest.mark.asyncio
async def test_update_system_category_name_still_rejected(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    from fastapi import HTTPException

    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = CategoryService(db_session)

    system_cat = await svc.create(ctx, CategoryCreate(name="System Test 2", is_income=False))
    system_cat.is_system = True
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, system_cat.id, CategoryUpdate(name="Renamed"))
    assert exc_info.value.status_code == 409
