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
from app.schemas.real_estate import PropertyCreate, PropertyUpdate, ValuationCreate
from app.services.account import AccountService
from app.services.real_estate import RealEstateService


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
    account_type: AccountType = "real_estate",
    nickname: str = "My Home",
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


async def test_create_property(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="123 Main St"),
    )

    assert prop.id is not None
    assert prop.account_id == account.id
    assert prop.address == "123 Main St"
    assert prop.nickname == "My Home"


async def test_get_property(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Beach House")

    svc = RealEstateService(db_session)
    created = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="456 Ocean Dr"),
    )

    fetched = await svc.get(ctx, created.id)
    assert fetched.id == created.id
    assert fetched.address == "456 Ocean Dr"


async def test_get_property_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = RealEstateService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_create_property_wrong_account_type(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="checking", nickname="Checking")

    svc = RealEstateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            PropertyCreate(account_id=account.id, address="789 Wrong St"),
        )
    assert exc_info.value.status_code == 400


async def test_create_property_duplicate(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Duplex")

    svc = RealEstateService(db_session)
    await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="100 First Ave"),
    )

    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            ctx,
            PropertyCreate(account_id=account.id, address="100 First Ave Duplicate"),
        )
    assert exc_info.value.status_code == 409


async def test_update_property(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Cabin")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="Old Address Ln"),
    )

    updated = await svc.update(ctx, prop.id, PropertyUpdate(address="New Address Rd"))
    assert updated.address == "New Address Rd"
    assert updated.id == prop.id


async def test_update_property_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = RealEstateService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.update(ctx, uuid.uuid4(), PropertyUpdate(address="Nowhere"))
    assert exc_info.value.status_code == 404


async def test_list_valuations(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Condo")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="200 Condo Blvd"),
    )

    valuations = await svc.list_valuations(ctx, prop.id)
    assert valuations == []


async def test_list_valuations_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = RealEstateService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await svc.list_valuations(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_add_valuation(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Townhouse")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="300 Town Rd"),
    )

    valuation = await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(
            valuation_date=date(2025, 6, 1),
            estimated_value=Decimal("450000.00"),
            source="manual",
        ),
    )

    assert valuation.id is not None
    assert valuation.real_estate_property_id == prop.id
    assert valuation.estimated_value == Decimal("450000.00")
    assert valuation.valuation_date == date(2025, 6, 1)
    assert valuation.source == "manual"

    valuations = await svc.list_valuations(ctx, prop.id)
    assert len(valuations) == 1
    assert valuations[0].id == valuation.id


async def test_create_property_with_purchase_details(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Primary Residence")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(
            account_id=account.id,
            address="500 Maple Ave",
            purchase_date=date(2020, 3, 15),
            purchase_price=Decimal("350000.00"),
        ),
    )

    assert prop.purchase_date == date(2020, 3, 15)
    assert prop.purchase_price == Decimal("350000.00")


async def test_create_property_forbidden_for_dependent(
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

    svc = RealEstateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            dep_ctx,
            PropertyCreate(account_id=account.id, address="Forbidden St"),
        )
    assert exc_info.value.status_code == 403


async def test_create_property_forbidden_partner_private_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    """Partner should get 403 when creating property on primary's private RE account."""
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    # Create account owned by primary_member (private)
    account = await _make_account(
        db_session,
        primary_ctx,
        nickname="Primary Private Home",
        owner_member_id=primary_member.id,
    )

    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    partner_ctx = VisibilityContext(
        user_id=partner_user.id,
        member_id=partner_member.id,
        role="partner",
        household_id=household.id,
    )

    svc = RealEstateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(
            partner_ctx,
            PropertyCreate(account_id=account.id, address="Partner Forbidden St"),
        )
    assert exc_info.value.status_code == 403


async def test_get_property_current_value_after_valuation(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Investment Property")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(account_id=account.id, address="600 Investment Dr"),
    )

    # Before any valuation, current value should be None
    fetched = await svc.get(ctx, prop.id)
    assert fetched.current_estimated_value is None
    assert fetched.current_value_as_of is None

    # Add a valuation
    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(
            valuation_date=date(2025, 9, 1),
            estimated_value=Decimal("275000.00"),
        ),
    )

    # Now should show the latest valuation
    updated = await svc.get(ctx, prop.id)
    assert updated.current_estimated_value == Decimal("275000.00")
    assert updated.current_value_as_of == date(2025, 9, 1)
