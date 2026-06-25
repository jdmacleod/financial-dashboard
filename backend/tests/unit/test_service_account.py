from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS
from app.core.visibility import VisibilityContext
from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.schemas.account import AccessGrantCreate, AccountCreate, AccountUpdate
from app.schemas.real_estate import PropertyCreate, ValuationCreate
from app.services.account import AccountService
from app.services.real_estate import RealEstateService


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id, member_id=member.id, role=role, household_id=household.id
    )


async def _latest_audit_row(db_session: AsyncSession, action: str) -> AuditLog:
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )
    return result.scalars().first()


def _assert_no_excluded_fields(row: AuditLog) -> None:
    for field in AUDIT_EXCLUDED_FIELDS:
        assert field not in (row.previous_value or {})
        assert field not in (row.new_value or {})


async def test_create_audit_row_excludes_pii(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    await service.create(
        ctx,
        AccountCreate(
            account_type="checking",
            nickname="Chase Checking",
            institution_name="Chase Bank",
            account_number="1234567890",
            routing_number="021000021",
        ),
    )
    row = await _latest_audit_row(db_session, "account.created")
    _assert_no_excluded_fields(row)


async def test_update_audit_row_excludes_pii_even_when_unchanged(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(
            account_type="checking",
            nickname="Chase Checking",
            institution_name="Chase Bank",
            account_number="1234567890",
        ),
    )
    await service.update(ctx, account.id, AccountUpdate(nickname="Renamed Checking"))
    row = await _latest_audit_row(db_session, "account.updated")
    _assert_no_excluded_fields(row)
    assert row.new_value["nickname"] == "Renamed Checking"


async def test_deactivate_audit_row_excludes_pii(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(account_type="checking", nickname="Chase", institution_name="Chase Bank"),
    )
    await service.deactivate(ctx, account.id)
    row = await _latest_audit_row(db_session, "account.deactivated")
    _assert_no_excluded_fields(row)


async def test_non_owner_partner_cannot_update_another_members_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner = await make_member(role="partner", display_name="Owner")
    other_partner = await make_member(role="partner", display_name="Other")
    other_user = await make_user(other_partner, "other@example.com")

    service = AccountService(db_session)
    owner_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        owner_ctx,
        AccountCreate(account_type="checking", nickname="Owner Checking", owner_member_id=owner.id),
    )

    other_ctx = _ctx(household, other_partner, "partner", other_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.update(other_ctx, account.id, AccountUpdate(nickname="Hacked"))
    assert exc_info.value.status_code in (403, 404)


async def test_create_seeds_tax_treatment_from_type(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A new retirement account inherits its tax treatment from the account type
    when the caller doesn't specify one (RMD eligibility stays correct)."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="retirement_401k", nickname="My 401k")
    )
    assert account.tax_treatment == "pretax"


async def test_create_unmapped_type_leaves_tax_treatment_null(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A type with no default mapping (checking) is left unclassified."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(ctx, AccountCreate(account_type="checking", nickname="Chase"))
    assert account.tax_treatment is None


async def test_create_explicit_tax_treatment_overrides_default(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """An explicit tax_treatment wins over the type-based default (after-tax 401k)."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(account_type="retirement_401k", nickname="Roth 401k", tax_treatment="roth"),
    )
    assert account.tax_treatment == "roth"


async def test_update_overrides_tax_treatment(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A correction via update changes the stored tax treatment."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="retirement_ira", nickname="Generic IRA")
    )
    assert account.tax_treatment == "pretax"
    updated = await service.update(ctx, account.id, AccountUpdate(tax_treatment="roth"))
    assert updated.tax_treatment == "roth"


async def test_update_can_clear_tax_treatment_to_null(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Setting tax_treatment explicitly to None clears it (unclassified)."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="retirement_ira", nickname="Generic IRA")
    )
    updated = await service.update(ctx, account.id, AccountUpdate(tax_treatment=None))
    assert updated.tax_treatment is None


async def test_update_omitting_tax_treatment_leaves_it_unchanged(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """An update that doesn't mention tax_treatment must not wipe it."""
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="retirement_401k", nickname="My 401k")
    )
    updated = await service.update(ctx, account.id, AccountUpdate(nickname="Renamed 401k"))
    assert updated.tax_treatment == "pretax"


async def test_create_grant_rejects_joint_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    grantee = await make_member(role="partner")
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Joint Checking")
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id))
    assert exc_info.value.status_code == 400


async def test_create_grant_rejects_self_grant_to_owner(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    owner = await make_member(role="partner")
    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx,
        AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id),
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(ctx, account.id, AccessGrantCreate(grantee_member_id=owner.id))
    assert exc_info.value.status_code == 400


async def test_create_grant_rejected_for_non_primary(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner = await make_member(role="partner")
    grantee = await make_member(role="partner", display_name="Grantee")
    partner_user = await make_user(owner, "owner@example.com")

    service = AccountService(db_session)
    primary_ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        primary_ctx,
        AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id),
    )

    partner_ctx = _ctx(household, owner, "partner", partner_user)
    with pytest.raises(HTTPException) as exc_info:
        await service.create_grant(
            partner_ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id)
        )
    assert exc_info.value.status_code == 403


async def test_create_and_revoke_grant_happy_path(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    owner = await make_member(role="partner")
    grantee = await make_member(role="partner", display_name="Grantee")

    service = AccountService(db_session)
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Owned", owner_member_id=owner.id)
    )
    grant = await service.create_grant(
        ctx, account.id, AccessGrantCreate(grantee_member_id=grantee.id)
    )
    assert grant.is_active is True

    await service.revoke_grant(ctx, account.id, grant.id)
    grants = await service.list_grants(ctx, account.id)
    assert all(g.id != grant.id for g in grants)


# ---------------------------------------------------------------------------
# B1 — list_accounts populates current_balance for real_estate (Phase 8)
# ---------------------------------------------------------------------------


async def test_list_accounts_real_estate_shows_valuation_balance(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """current_balance for a real_estate account reflects the latest PropertyValuation,
    not a missing AccountSnapshot. Verifies the two-step batch pattern in list_accounts().
    """
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    re_account = await service.create(
        ctx, AccountCreate(account_type="real_estate", nickname="My Home")
    )

    re_svc = RealEstateService(db_session)
    prop = await re_svc.create(ctx, PropertyCreate(account_id=re_account.id, address="1 Main St"))
    await re_svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date.today(), estimated_value=Decimal("500000")),
    )

    accounts = await service.list_accounts(ctx)
    re_response = next(a for a in accounts if a.id == re_account.id)

    assert re_response.current_balance == Decimal("500000")
    assert re_response.balance_as_of == date.today()


async def test_list_accounts_real_estate_no_valuation_shows_zero(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Real estate account with a property record but no valuation shows zero balance."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    re_account = await service.create(
        ctx, AccountCreate(account_type="real_estate", nickname="Empty Lot")
    )

    re_svc = RealEstateService(db_session)
    await re_svc.create(ctx, PropertyCreate(account_id=re_account.id, address="2 Main St"))

    accounts = await service.list_accounts(ctx)
    re_response = next(a for a in accounts if a.id == re_account.id)

    assert re_response.current_balance == Decimal("0")


async def test_list_accounts_real_estate_orphan_no_property_returns_none(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """RE account with no property record (data gap) falls through to the snapshot
    path and returns None balance — no KeyError, no crash.
    """
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    re_account = await service.create(
        ctx, AccountCreate(account_type="real_estate", nickname="Orphan RE")
    )

    accounts = await service.list_accounts(ctx)
    re_response = next(a for a in accounts if a.id == re_account.id)

    assert re_response.current_balance is None


async def test_list_accounts_transaction_account_uses_transaction_sum(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Transaction-based accounts (checking, savings, credit_card, etc.) derive
    current_balance from SUM(transaction.amount), not from AccountSnapshot.
    """
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    checking = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Chase Checking")
    )

    now = datetime.now(UTC)
    for amount in [Decimal("3000"), Decimal("1500"), Decimal("-200")]:
        db_session.add(
            Transaction(
                account_id=checking.id,
                transaction_date=date(2025, 6, 1),
                amount=amount,
                tags=[],
                source="manual",
                created_at=now,
                updated_at=now,
            )
        )
    await db_session.flush()

    accounts = await service.list_accounts(ctx)
    checking_response = next(a for a in accounts if a.id == checking.id)

    assert checking_response.current_balance == Decimal("4300")
    assert checking_response.balance_as_of is None


async def test_list_accounts_transaction_account_no_transactions_returns_none(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A transaction-based account with no transactions returns None balance (not zero)."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    checking = await service.create(
        ctx, AccountCreate(account_type="checking", nickname="Empty Checking")
    )

    accounts = await service.list_accounts(ctx)
    checking_response = next(a for a in accounts if a.id == checking.id)

    assert checking_response.current_balance is None


async def test_list_accounts_investment_account_still_uses_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Valuation-based accounts (investments, pension) still use AccountSnapshot."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    brokerage = await service.create(
        ctx, AccountCreate(account_type="investment_brokerage", nickname="Fidelity")
    )

    snap = AccountSnapshot(
        account_id=brokerage.id,
        snapshot_date=date(2025, 6, 30),
        balance=Decimal("95000"),
        source="manual",
        created_at=datetime.now(UTC),
    )
    db_session.add(snap)
    await db_session.flush()

    accounts = await service.list_accounts(ctx)
    brokerage_response = next(a for a in accounts if a.id == brokerage.id)

    assert brokerage_response.current_balance == Decimal("95000")
    assert brokerage_response.balance_as_of == date(2025, 6, 30)


async def test_list_accounts_heloc_uses_transaction_sum(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """heloc is in _TRANSACTION_BASED_TYPES — balance must come from SUM(transactions),
    not from AccountSnapshot (which would return None for a non-investment account type
    that was accidentally excluded from the set)."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    service = AccountService(db_session)
    heloc = await service.create(ctx, AccountCreate(account_type="heloc", nickname="Chase HELOC"))

    now = datetime.now(UTC)
    for amount in [Decimal("-92000"), Decimal("-920"), Decimal("920")]:
        db_session.add(
            Transaction(
                account_id=heloc.id,
                transaction_date=date(2024, 1, 31),
                amount=amount,
                tags=[],
                source="manual",
                created_at=now,
                updated_at=now,
            )
        )
    await db_session.flush()

    accounts = await service.list_accounts(ctx)
    heloc_response = next(a for a in accounts if a.id == heloc.id)

    assert heloc_response.current_balance == Decimal("-92000")
    assert heloc_response.balance_as_of is None
