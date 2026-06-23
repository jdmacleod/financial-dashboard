from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.repositories.pension import PensionRepository
from app.schemas.account import AccountCreate, AccountType
from app.schemas.pension import PensionAccountCreate, PensionAccountUpdate
from app.services.account import AccountService
from app.services.pension import PensionService


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
    account_type: AccountType = "pension",
    nickname: str = "My Pension",
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


async def test_create_pension(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    pension = await svc.create(
        ctx,
        account.id,
        PensionAccountCreate(
            plan_name="State Teachers Retirement",
            monthly_benefit_estimate=Decimal("3500.00"),
            eligibility_age=62,
            is_vested=True,
        ),
    )

    assert pension.id is not None
    assert pension.account_id == account.id
    assert pension.is_vested is True
    assert pension.monthly_benefit_estimate == Decimal("3500.00")
    assert pension.eligibility_age == 62


async def test_create_pension_wrong_account_type(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="checking", nickname="Checking")

    svc = PensionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(ctx, account.id, PensionAccountCreate())
    assert exc_info.value.status_code == 400


async def test_create_pension_duplicate(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    await svc.create(ctx, account.id, PensionAccountCreate())

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(ctx, account.id, PensionAccountCreate())
    assert exc_info.value.status_code == 409


async def test_get_pension(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    await svc.create(
        ctx,
        account.id,
        PensionAccountCreate(plan_name="PERS", administrator="State Board"),
    )

    fetched = await svc.get(ctx, account.id)
    assert fetched.plan_name == "PERS"
    assert fetched.administrator == "State Board"


async def test_get_pension_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, account.id)
    assert exc_info.value.status_code == 404


async def test_update_pension_model_fields_set(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """PATCH semantics: only fields in model_fields_set are updated."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    await svc.create(
        ctx,
        account.id,
        PensionAccountCreate(
            monthly_benefit_estimate=Decimal("2000.00"),
            eligibility_age=65,
            is_vested=False,
        ),
    )

    # PATCH only is_vested — other fields should be unchanged
    updated = await svc.update(ctx, account.id, PensionAccountUpdate(is_vested=True))
    assert updated.is_vested is True
    assert updated.monthly_benefit_estimate == Decimal("2000.00")
    assert updated.eligibility_age == 65


async def test_update_pension_cola_null_guard(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """cola_adjustment_rate must not be set to null (NOT NULL in DB)."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    await svc.create(
        ctx,
        account.id,
        PensionAccountCreate(cola_adjustment_rate=Decimal("0.03")),
    )

    # PATCH with cola_adjustment_rate=None — should be ignored, not written
    updated = await svc.update(ctx, account.id, PensionAccountUpdate(cola_adjustment_rate=None))
    # Original value preserved
    assert updated.cola_adjustment_rate == Decimal("0.0300")


async def test_pension_encrypted_fields_excluded_from_audit(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """plan_name and administrator are encrypted — must not appear in audit_log."""
    from sqlalchemy import select

    from app.db.models.audit_log import AuditLog

    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    await svc.create(
        ctx,
        account.id,
        PensionAccountCreate(
            plan_name="Secret Plan",
            administrator="Secret Admin",
        ),
    )
    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "pension.created",
        )
    )
    log_entries = result.scalars().all()
    assert len(log_entries) == 1
    new_val = log_entries[0].new_value or {}
    assert "plan_name_enc" not in new_val
    assert "administrator_enc" not in new_val
    assert "notes_enc" not in new_val


async def test_update_pension_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = PensionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, account.id, PensionAccountUpdate(is_vested=True))
    assert exc_info.value.status_code == 404


async def test_create_pension_forbidden_for_dependent(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, primary_ctx)

    dep_member = await make_member(role="dependent", display_name="Dependent")
    dep_user = await make_user(dep_member, "dep@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    svc = PensionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(dep_ctx, account.id, PensionAccountCreate())
    assert exc_info.value.status_code == 403


async def test_update_pension_forbidden_for_dependent(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, primary_ctx)

    svc = PensionService(db_session)
    await svc.create(primary_ctx, account.id, PensionAccountCreate(is_vested=True))

    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep2@example.com")
    dep_ctx = VisibilityContext(
        user_id=dep_user.id,
        member_id=dep_member.id,
        role="dependent",
        household_id=household.id,
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(dep_ctx, account.id, PensionAccountUpdate(is_vested=False))
    assert exc_info.value.status_code == 403


async def test_create_pension_rbac_denied_for_partner_private(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(
        db_session, primary_ctx, owner_member_id=primary_member.id, nickname="Primary Pension"
    )

    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    partner_ctx = VisibilityContext(
        user_id=partner_user.id,
        member_id=partner_member.id,
        role="partner",
        household_id=household.id,
    )

    svc = PensionService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(partner_ctx, account.id, PensionAccountCreate())
    assert exc_info.value.status_code == 404


# --- Estimate history -------------------------------------------------------


async def test_create_records_initial_estimate(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = PensionService(db_session)
    pension = await svc.create(
        ctx, account.id, PensionAccountCreate(monthly_benefit_estimate=Decimal("3500.00"))
    )

    history = await PensionRepository(db_session).get_estimate_history(pension.id)
    assert len(history) == 1
    assert history[0].monthly_benefit_estimate == Decimal("3500.00")
    assert history[0].effective_date == datetime.now(UTC).date()


async def test_update_estimate_records_new_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = PensionService(db_session)
    pension = await svc.create(
        ctx, account.id, PensionAccountCreate(monthly_benefit_estimate=Decimal("3500.00"))
    )

    await svc.update(
        ctx, account.id, PensionAccountUpdate(monthly_benefit_estimate=Decimal("4000.00"))
    )

    history = await PensionRepository(db_session).get_estimate_history(pension.id)
    # Create + same-day update upsert to one row carrying the latest estimate.
    assert history[-1].monthly_benefit_estimate == Decimal("4000.00")


async def test_update_non_pv_field_does_not_change_estimate(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = PensionService(db_session)
    pension = await svc.create(
        ctx, account.id, PensionAccountCreate(monthly_benefit_estimate=Decimal("3500.00"))
    )

    # Editing a non-PV field (notes) must not alter the recorded estimate.
    await svc.update(ctx, account.id, PensionAccountUpdate(notes="reviewed"))

    history = await PensionRepository(db_session).get_estimate_history(pension.id)
    assert len(history) == 1
    assert history[0].monthly_benefit_estimate == Decimal("3500.00")
