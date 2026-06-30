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
from app.repositories.real_estate import RealEstateRepository
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
    # AccountRepository.get_by_id hides inaccessible accounts as 404 (not 403)
    # to prevent resource enumeration — private accounts are invisible to partners
    assert exc_info.value.status_code == 404


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


async def test_get_equity_no_mortgage(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Equity House")

    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="1 Equity Lane"))

    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 1), estimated_value=Decimal("500000.00")),
    )
    await db_session.flush()

    equity = await svc.get_equity(ctx, prop.id)
    assert equity.property_value == Decimal("500000.00")
    assert equity.mortgage_balance is None
    assert equity.equity == Decimal("500000.00")
    assert equity.mortgage_balance_visible is True


async def test_get_equity_no_valuation(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="No Val House")

    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="2 Empty Lane"))

    with pytest.raises(HTTPException) as exc_info:
        await svc.get_equity(ctx, prop.id)
    assert exc_info.value.status_code == 404


async def test_get_by_account_returns_property(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Lookup House")

    svc = RealEstateService(db_session)
    await svc.create(ctx, PropertyCreate(account_id=account.id, address="99 Lookup Ave"))

    result = await svc.get_by_account(ctx, account.id)
    assert result.account_id == account.id
    assert result.address == "99 Lookup Ave"


async def test_get_by_account_no_property_returns_404(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Empty RE")

    svc = RealEstateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_by_account(ctx, account.id)
    assert exc_info.value.status_code == 404


async def test_get_equity_property_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    import uuid as _uuid

    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = RealEstateService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get_equity(ctx, _uuid.uuid4())
    assert exc_info.value.status_code == 404


async def test_get_equity_mortgage_invisible(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: Any,
    make_user: Any,
) -> None:
    """Partner sees mortgage_balance_visible=False for a mortgage owned by primary only."""
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)

    # Mortgage account owned by primary only (private)
    mortgage_account = await _make_account(
        db_session,
        primary_ctx,
        account_type="mortgage",
        nickname="Primary Mortgage",
        owner_member_id=primary_member.id,
    )
    # RE account jointly visible
    re_account = await _make_account(db_session, primary_ctx, nickname="Our House")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        primary_ctx,
        PropertyCreate(
            account_id=re_account.id,
            address="7 Private Ln",
            linked_mortgage_account_id=mortgage_account.id,
        ),
    )
    await svc.add_valuation(
        primary_ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 1), estimated_value=Decimal("400000.00")),
    )
    await db_session.flush()

    partner_member = await make_member(role="partner", display_name="Partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    partner_ctx = VisibilityContext(
        user_id=partner_user.id,
        member_id=partner_member.id,
        role="partner",
        household_id=household.id,
    )

    equity = await svc.get_equity(partner_ctx, prop.id)
    assert equity.mortgage_balance_visible is False
    assert equity.mortgage_balance is None
    assert equity.equity is None


async def test_update_property_uses_model_fields_set(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """PATCH semantics: only fields in model_fields_set are updated."""
    from app.schemas.real_estate import PropertyCreate, PropertyUpdate

    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, nickname="Patch House")

    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(
            account_id=account.id,
            address="123 Old St",
            purchase_price=Decimal("300000.00"),
        ),
    )

    # PATCH only address — purchase_price must remain unchanged
    updated = await svc.update(ctx, prop.id, PropertyUpdate(address="456 New St"))
    assert updated.address == "456 New St"
    assert updated.purchase_price == Decimal("300000.00")


# ---------------------------------------------------------------------------
# RealEstateRepository.latest_valuation_as_of tests
# ---------------------------------------------------------------------------


async def test_latest_valuation_as_of_returns_most_recent_before_date(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="1 Main St"))

    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2024, 6, 1), estimated_value=Decimal("300000")),
    )
    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 1), estimated_value=Decimal("350000")),
    )
    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 6, 1), estimated_value=Decimal("400000")),
    )

    repo = RealEstateRepository(db_session)
    result = await repo.latest_valuation_as_of(prop.id, date(2025, 3, 31))

    assert result is not None
    assert result.estimated_value == Decimal("350000")
    assert result.valuation_date == date(2025, 1, 1)


async def test_latest_valuation_as_of_exact_date_match(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="2 Main St"))

    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 3, 15), estimated_value=Decimal("425000")),
    )

    repo = RealEstateRepository(db_session)
    result = await repo.latest_valuation_as_of(prop.id, date(2025, 3, 15))

    assert result is not None
    assert result.estimated_value == Decimal("425000")


async def test_latest_valuation_as_of_returns_none_when_all_after(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="3 Main St"))

    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 6, 1), estimated_value=Decimal("500000")),
    )

    repo = RealEstateRepository(db_session)
    result = await repo.latest_valuation_as_of(prop.id, date(2025, 1, 1))

    assert result is None


async def test_latest_valuation_as_of_returns_none_when_no_valuations(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    svc = RealEstateService(db_session)
    prop = await svc.create(ctx, PropertyCreate(account_id=account.id, address="4 Main St"))

    repo = RealEstateRepository(db_session)
    result = await repo.latest_valuation_as_of(prop.id, date(2025, 12, 31))

    assert result is None


async def test_get_equity_uses_transaction_balance_for_mortgage(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Regression: a manually-added mortgage has transactions but no snapshot.

    Equity used to read the snapshot table only, so the mortgage balance came
    back None and the equity bar vanished. It must now resolve the balance from
    the linked account's transactions, exactly like the Accounts ledger does.
    """
    from app.schemas.transaction import TransactionCreate
    from app.services.transaction import TransactionService

    ctx = _ctx(household, primary_member, "primary", primary_user)
    mortgage_account = await _make_account(
        db_session, ctx, account_type="mortgage", nickname="New Mortgage"
    )
    # Two transactions sum to -250000 owed. No snapshot is ever written.
    txn_svc = TransactionService(db_session)
    await txn_svc.create(
        ctx,
        mortgage_account.id,
        TransactionCreate(transaction_date=date(2025, 1, 1), amount=Decimal("-260000.00")),
    )
    await txn_svc.create(
        ctx,
        mortgage_account.id,
        TransactionCreate(transaction_date=date(2025, 6, 1), amount=Decimal("10000.00")),
    )

    re_account = await _make_account(db_session, ctx, nickname="Linked House")
    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(
            account_id=re_account.id,
            address="9 Mortgaged Way",
            linked_mortgage_account_id=mortgage_account.id,
        ),
    )
    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 1), estimated_value=Decimal("500000.00")),
    )
    await db_session.flush()

    equity = await svc.get_equity(ctx, prop.id)
    assert equity.mortgage_balance == Decimal("250000.00")
    assert equity.equity == Decimal("250000.00")
    assert equity.mortgage_balance_visible is True


async def test_get_equity_linked_mortgage_without_balance_is_distinct_from_unlinked(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A linked mortgage with no transactions/snapshot yet reports a null balance
    and null equity (not full property value) — that's how the UI tells 'linked,
    no balance recorded yet' apart from 'no mortgage linked' (full equity)."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    mortgage_account = await _make_account(
        db_session, ctx, account_type="mortgage", nickname="Empty Mortgage"
    )
    re_account = await _make_account(db_session, ctx, nickname="House With Empty Mortgage")
    svc = RealEstateService(db_session)
    prop = await svc.create(
        ctx,
        PropertyCreate(
            account_id=re_account.id,
            address="11 Pending Ln",
            linked_mortgage_account_id=mortgage_account.id,
        ),
    )
    await svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 1), estimated_value=Decimal("400000.00")),
    )
    await db_session.flush()

    equity = await svc.get_equity(ctx, prop.id)
    assert equity.mortgage_balance is None
    assert equity.equity is None  # NOT 400000 — that would mean "no mortgage linked"
    assert equity.mortgage_balance_visible is True
