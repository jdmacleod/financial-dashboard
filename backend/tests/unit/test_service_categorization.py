"""Direct-call unit tests for CategorizationService.

These call the service methods in-process (not through the API) so every branch
is exercised and reliably attributed to coverage in any environment.
"""

import uuid
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.audit_log import AuditLog
from app.db.models.category import Category
from app.db.models.transaction import Transaction
from app.schemas.category_rule import CategoryRuleCreate, CategoryRuleUpdate
from app.services.categorization import CategorizationService


def _now() -> datetime:
    return datetime.now(UTC)


async def _category(db: AsyncSession, household_id: uuid.UUID, name: str) -> Category:
    cat = Category(
        household_id=household_id, name=name, is_income=False, is_system=False, created_at=_now()
    )
    db.add(cat)
    await db.flush()
    return cat


async def _account(db: AsyncSession, household_id: uuid.UUID) -> Account:
    acct = Account(
        household_id=household_id,
        account_type="checking",
        nickname="Cat Test",
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(acct)
    await db.flush()
    return acct


async def _txn(
    db: AsyncSession, account_id: uuid.UUID, payee: str, category_id: uuid.UUID | None
) -> Transaction:
    t = Transaction(
        account_id=account_id,
        transaction_date=_now().date(),
        amount=-10,
        payee_normalized=payee,
        category_id=category_id,
        is_transfer=False,
        tags=[],
        source="manual",
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(t)
    await db.flush()
    return t


async def test_create_list_update_delete_and_audit(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    coffee = await _category(db_session, primary_ctx.household_id, "Coffee")

    rule = await svc.create(
        primary_ctx, CategoryRuleCreate(pattern="STARBUCKS", category_id=coffee.id)
    )
    assert rule.match_type == "contains"
    assert (await svc.list_rules(primary_ctx))[0].id == rule.id

    updated = await svc.update(primary_ctx, rule.id, CategoryRuleUpdate(priority=7))
    assert updated.priority == 7

    await svc.delete(primary_ctx, rule.id)
    assert await svc.list_rules(primary_ctx) == []

    # created + updated + deleted audit events all landed.
    actions = (
        (
            await db_session.execute(
                select(AuditLog.action).where(AuditLog.entity_type == "category_rule")
            )
        )
        .scalars()
        .all()
    )
    assert set(actions) == {
        "category_rule.created",
        "category_rule.updated",
        "category_rule.deleted",
    }


async def test_create_rejects_unknown_category_and_bad_regex(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    with pytest.raises(HTTPException) as unknown:
        await svc.create(primary_ctx, CategoryRuleCreate(pattern="X", category_id=uuid.uuid4()))
    assert unknown.value.status_code == 400

    coffee = await _category(db_session, primary_ctx.household_id, "Coffee")
    with pytest.raises(HTTPException) as bad_regex:
        await svc.create(
            primary_ctx,
            CategoryRuleCreate(pattern="([oops", match_type="regex", category_id=coffee.id),
        )
    assert bad_regex.value.status_code == 400


async def test_non_writer_forbidden(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    coffee = await _category(db_session, primary_ctx.household_id, "Coffee")
    dependent = replace(primary_ctx, role="dependent")
    with pytest.raises(HTTPException) as exc:
        await svc.create(dependent, CategoryRuleCreate(pattern="X", category_id=coffee.id))
    assert exc.value.status_code == 403


async def test_update_and_delete_not_found(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    with pytest.raises(HTTPException) as u:
        await svc.update(primary_ctx, uuid.uuid4(), CategoryRuleUpdate(priority=1))
    assert u.value.status_code == 404
    with pytest.raises(HTTPException) as d:
        await svc.delete(primary_ctx, uuid.uuid4())
    assert d.value.status_code == 404


async def test_match_respects_priority_and_active(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    coffee = await _category(db_session, primary_ctx.household_id, "Coffee")
    treats = await _category(db_session, primary_ctx.household_id, "Treats")
    await svc.create(
        primary_ctx, CategoryRuleCreate(pattern="STARBUCKS", category_id=coffee.id, priority=1)
    )
    hi = await svc.create(
        primary_ctx, CategoryRuleCreate(pattern="STARBUCKS", category_id=treats.id, priority=9)
    )
    assert await svc.match(primary_ctx.household_id, "STARBUCKS RESERVE") == treats.id
    assert await svc.match(primary_ctx.household_id, "nothing matches") is None
    assert await svc.match(primary_ctx.household_id, None) is None

    # Deactivate the winner → the lower-priority rule takes over.
    await svc.update(primary_ctx, hi.id, CategoryRuleUpdate(is_active=False))
    assert await svc.match(primary_ctx.household_id, "STARBUCKS") == coffee.id


async def test_suggest_from_history(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    assert await svc.suggest_from_history(primary_ctx) == []  # no accounts yet

    dining = await _category(db_session, primary_ctx.household_id, "Dining")
    acct = await _account(db_session, primary_ctx.household_id)
    for _ in range(3):
        await _txn(db_session, acct.id, "CHIPOTLE ONLINE", dining.id)
    await _txn(db_session, acct.id, "ONE OFF SHOP", dining.id)  # below threshold

    suggestions = await svc.suggest_from_history(primary_ctx)
    chipotle = [s for s in suggestions if "CHIPOTLE" in s.pattern]
    assert chipotle and chipotle[0].category_id == dining.id and chipotle[0].occurrences == 3
    assert chipotle[0].category_name == "Dining"
    assert not any("ONE OFF" in s.pattern for s in suggestions)

    # A payee already covered by an active rule is not re-suggested.
    await svc.create(primary_ctx, CategoryRuleCreate(pattern="CHIPOTLE", category_id=dining.id))
    assert not any("CHIPOTLE" in s.pattern for s in await svc.suggest_from_history(primary_ctx))


async def test_backfill_fills_empty_only(
    db_session: AsyncSession, primary_ctx: VisibilityContext
) -> None:
    svc = CategorizationService(db_session)
    assert await svc.backfill_uncategorized(primary_ctx) == 0  # no accounts / no rules

    dining = await _category(db_session, primary_ctx.household_id, "Dining")
    other = await _category(db_session, primary_ctx.household_id, "Other")
    acct = await _account(db_session, primary_ctx.household_id)
    uncategorized = await _txn(db_session, acct.id, "CHIPOTLE ONLINE", None)
    already_set = await _txn(db_session, acct.id, "CHIPOTLE DOWNTOWN", other.id)
    await svc.create(primary_ctx, CategoryRuleCreate(pattern="CHIPOTLE", category_id=dining.id))

    assert await svc.backfill_uncategorized(primary_ctx) == 1
    await db_session.refresh(uncategorized)
    await db_session.refresh(already_set)
    assert uncategorized.category_id == dining.id
    assert already_set.category_id == other.id  # never overridden

    audited = await db_session.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "transaction.categorized_by_rule")
    )
    assert audited.scalar_one() == 1
