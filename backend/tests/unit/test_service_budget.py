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
from app.schemas.budget import BudgetCreate, BudgetUpdate
from app.services.budget import BudgetService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
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


async def test_list_budgets(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("300.00"),
            effective_from=date(2025, 1, 1),
        ),
    )

    budgets = await svc.list_budgets(ctx)
    assert len(budgets) >= 1
    assert any(b.category_id == cat.id for b in budgets)


async def test_create_budget(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    budget = await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("100.00"),
            effective_from=date(2025, 1, 1),
        ),
    )

    assert budget.id is not None
    assert budget.household_id == household.id
    assert budget.category_id == cat.id
    assert budget.amount == Decimal("100.00")
    assert budget.effective_from == date(2025, 1, 1)
    assert budget.period == "monthly"


async def test_create_budget_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    cat = await _make_category(db_session, household)

    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    svc = BudgetService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            dep_ctx,
            BudgetCreate(
                category_id=cat.id,
                amount=Decimal("100.00"),
                effective_from=date(2025, 1, 1),
            ),
        )
    assert exc_info.value.status_code == 403


async def test_update_budget(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    budget = await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("200.00"),
            effective_from=date(2025, 1, 1),
        ),
    )

    updated = await svc.update(ctx, budget.id, BudgetUpdate(amount=Decimal("250.00")))
    assert updated.amount == Decimal("250.00")


async def test_update_budget_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = BudgetService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, uuid.uuid4(), BudgetUpdate(amount=Decimal("999.00")))
    assert exc_info.value.status_code == 404


async def test_update_budget_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    budget = await svc.create(
        primary_ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("150.00"),
            effective_from=date(2025, 1, 1),
        ),
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
        await svc.update(dep_ctx, budget.id, BudgetUpdate(amount=Decimal("999.00")))
    assert exc_info.value.status_code == 403


async def test_delete_budget(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    budget = await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("400.00"),
            effective_from=date(2025, 1, 1),
        ),
    )

    await svc.delete(ctx, budget.id)

    budgets = await svc.list_budgets(ctx, category_id=cat.id)
    assert not any(b.id == budget.id for b in budgets)


async def test_delete_budget_forbidden(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    cat = await _make_category(db_session, household)

    svc = BudgetService(db_session)
    budget = await svc.create(
        primary_ctx,
        BudgetCreate(
            category_id=cat.id,
            amount=Decimal("500.00"),
            effective_from=date(2025, 1, 1),
        ),
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
        await svc.delete(dep_ctx, budget.id)
    assert exc_info.value.status_code == 403


async def test_delete_budget_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = BudgetService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.delete(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_list_budgets_filter_by_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    cat1 = await _make_category(db_session, household)
    cat2 = Category(
        household_id=household.id,
        name="Dining",
        is_income=False,
        is_system=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(cat2)
    await db_session.flush()

    svc = BudgetService(db_session)
    await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat1.id,
            amount=Decimal("100.00"),
            effective_from=date(2025, 1, 1),
        ),
    )
    await svc.create(
        ctx,
        BudgetCreate(
            category_id=cat2.id,
            amount=Decimal("200.00"),
            effective_from=date(2025, 1, 1),
        ),
    )

    filtered = await svc.list_budgets(ctx, category_id=cat1.id)
    assert all(b.category_id == cat1.id for b in filtered)
    assert len(filtered) >= 1
