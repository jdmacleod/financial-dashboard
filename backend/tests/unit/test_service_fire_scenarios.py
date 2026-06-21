"""Integration tests for FireScenarioService (uses real DB via savepoint pattern)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.schemas.fire import FireScenarioCreate, FireScenarioUpdate, IncomeStream, IncomeStreamType
from app.services.fire_service import FireScenarioService


def _ctx(
    household: Household,
    member: HouseholdMember,
    role: str,
    user: User,
) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


async def test_create_scenario(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    scenario = await svc.create(
        ctx,
        FireScenarioCreate(
            name="Lean FIRE",
            target_annual_spend=Decimal("40000"),
        ),
    )

    assert scenario.id is not None
    assert scenario.name == "Lean FIRE"
    assert scenario.target_annual_spend == Decimal("40000")
    assert scenario.safe_withdrawal_rate == Decimal("0.04")
    assert scenario.household_id == household.id


async def test_list_scenarios(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    await svc.create(ctx, FireScenarioCreate(name="Lean", target_annual_spend=Decimal("40000")))
    await svc.create(ctx, FireScenarioCreate(name="Fat", target_annual_spend=Decimal("100000")))

    scenarios = await svc.list(ctx)
    names = {s.name for s in scenarios}
    assert "Lean" in names
    assert "Fat" in names
    assert len(scenarios) >= 2


async def test_update_scenario(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    created = await svc.create(
        ctx, FireScenarioCreate(name="Draft", target_annual_spend=Decimal("50000"))
    )

    updated = await svc.update(
        ctx,
        created.id,
        FireScenarioUpdate(name="Final", target_annual_spend=Decimal("55000")),
    )

    assert updated.name == "Final"
    assert updated.target_annual_spend == Decimal("55000")
    assert updated.id == created.id


async def test_delete_scenario(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    created = await svc.create(
        ctx, FireScenarioCreate(name="ToDelete", target_annual_spend=Decimal("60000"))
    )

    await svc.delete(ctx, created.id)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, created.id)
    assert exc_info.value.status_code == 404


async def test_detect_merges_streams(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """With transactions, detect() populates income_streams."""
    ctx = _ctx(household, primary_member, "primary", primary_user)

    # Create an income category and transactions
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    cat = Category(
        household_id=household.id,
        name="Salary",
        is_income=True,
        is_system=False,
        created_at=now,
    )
    db_session.add(cat)
    await db_session.flush()

    # Create an account and some income transactions
    acct = Account(
        household_id=household.id,
        account_type="checking",
        nickname="Checking",
        include_in_net_worth=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(acct)
    await db_session.flush()

    for month_offset in range(6):
        txn = Transaction(
            account_id=acct.id,
            transaction_date=date(2025, max(1, 7 - month_offset), 1),
            amount=Decimal("5000.00"),
            category_id=cat.id,
            is_transfer=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(txn)
    await db_session.flush()

    svc = FireScenarioService(db_session)
    scenario = await svc.create(
        ctx, FireScenarioCreate(name="Test", target_annual_spend=Decimal("50000"))
    )

    result = await svc.detect(ctx, scenario.id, trailing_months=12)
    detected = result.scenario

    assert detected.detected_annual_income is not None
    assert detected.detected_annual_income > Decimal(0)
    # Should have income streams from the salary category
    assert len(detected.additional_income_streams) > 0


async def test_detect_does_not_duplicate(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Running detect() twice should not duplicate auto-detected streams."""
    ctx = _ctx(household, primary_member, "primary", primary_user)

    from datetime import UTC, datetime

    now = datetime.now(UTC)
    cat = Category(
        household_id=household.id,
        name="Consulting fees",
        is_income=True,
        is_system=False,
        created_at=now,
    )
    db_session.add(cat)
    await db_session.flush()

    acct = Account(
        household_id=household.id,
        account_type="checking",
        nickname="Checking2",
        include_in_net_worth=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(acct)
    await db_session.flush()

    for i in range(3):
        txn = Transaction(
            account_id=acct.id,
            transaction_date=date(2025, 1 + i, 1),
            amount=Decimal("3000.00"),
            category_id=cat.id,
            is_transfer=False,
            created_at=now,
            updated_at=now,
        )
        db_session.add(txn)
    await db_session.flush()

    svc = FireScenarioService(db_session)
    scenario = await svc.create(
        ctx, FireScenarioCreate(name="NoDup", target_annual_spend=Decimal("40000"))
    )

    # Detect twice
    first = await svc.detect(ctx, scenario.id)
    second = await svc.detect(ctx, scenario.id)

    # Stream count after second detect should equal first detect count
    assert len(second.scenario.additional_income_streams) == len(
        first.scenario.additional_income_streams
    ), "Detecting twice should not duplicate streams"


async def test_detect_preserves_manual_streams(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Manual stream (auto_detected=False) should be preserved after re-detect."""
    ctx = _ctx(household, primary_member, "primary", primary_user)

    manual_stream = IncomeStream(
        id=str(uuid.uuid4()),
        label="Rental Property",
        type=IncomeStreamType.rental,
        amount_annual=Decimal("18000"),
        growth_rate_annual=Decimal("0.02"),
        start_year=2026,
        auto_detected=False,
    )

    svc = FireScenarioService(db_session)
    scenario = await svc.create(
        ctx,
        FireScenarioCreate(
            name="WithManual",
            target_annual_spend=Decimal("50000"),
            additional_income_streams=[manual_stream],
        ),
    )

    # Detect with no transactions (nothing to detect)
    result = await svc.detect(ctx, scenario.id)

    manual_streams = [s for s in result.scenario.additional_income_streams if not s.auto_detected]
    assert len(manual_streams) == 1
    assert manual_streams[0].label == "Rental Property"
    assert manual_streams[0].amount_annual == Decimal("18000")


async def test_project_returns_projections(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """project() should return a FireProjectionResponse with projections."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    scenario = await svc.create(
        ctx, FireScenarioCreate(name="Proj Test", target_annual_spend=Decimal("60000"))
    )

    result = await svc.project(ctx, scenario.id, from_year=2026)

    assert result.summary is not None
    assert len(result.projections) > 0
    assert result.summary.fire_number > Decimal(0)


async def test_create_fire_scenario_with_member_id(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """member_id is persisted on FireScenario and returned in the response."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    scenario = await svc.create(
        ctx,
        FireScenarioCreate(
            name="Member FIRE",
            target_annual_spend=Decimal("50000"),
            member_id=primary_member.id,
        ),
    )

    assert scenario.member_id == primary_member.id


async def test_update_fire_scenario_member_id(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """member_id can be set and cleared via update."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    created = await svc.create(
        ctx,
        FireScenarioCreate(name="Household FIRE", target_annual_spend=Decimal("60000")),
    )
    assert created.member_id is None

    with_member = await svc.update(ctx, created.id, FireScenarioUpdate(member_id=primary_member.id))
    assert with_member.member_id == primary_member.id

    cleared = await svc.update(ctx, created.id, FireScenarioUpdate(member_id=None))
    assert cleared.member_id is None


async def test_scenario_forbidden_for_dependent(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    """Dependent role should get 403 when trying to create a scenario."""
    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep_fire@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    svc = FireScenarioService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            dep_ctx,
            FireScenarioCreate(name="Forbidden", target_annual_spend=Decimal("50000")),
        )
    assert exc_info.value.status_code == 403


async def test_create_fire_scenario_with_foreign_member_raises_404(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """_assert_member_in_household raises 404 when member_id does not belong to the household."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    foreign_member_id = uuid.uuid4()  # random UUID — not in this household

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            FireScenarioCreate(
                name="Foreign Member FIRE",
                target_annual_spend=Decimal("50000"),
                member_id=foreign_member_id,
            ),
        )
    assert exc_info.value.status_code == 404
    assert "Member not found" in exc_info.value.detail


async def test_update_fire_scenario_with_foreign_member_raises_404(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """_assert_member_in_household raises 404 on update when member_id is from another household."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = FireScenarioService(db_session)

    created = await svc.create(
        ctx,
        FireScenarioCreate(name="Valid Scenario", target_annual_spend=Decimal("50000")),
    )

    foreign_member_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, created.id, FireScenarioUpdate(member_id=foreign_member_id))
    assert exc_info.value.status_code == 404
    assert "Member not found" in exc_info.value.detail
