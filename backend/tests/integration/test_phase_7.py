"""Phase 7 acceptance criteria — Real Estate & Pension Enhancement."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionAccount
from app.db.models.user import User
from app.schemas.account import AccountCreate
from app.services.account import AccountService

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def _make_account(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    account_type: str,
    nickname: str,
) -> str:
    from app.core.visibility import VisibilityContext

    ctx = VisibilityContext(
        user_id=primary_user.id,
        member_id=primary_member.id,
        role="primary",
        household_id=household.id,
    )
    svc = AccountService(db_session)
    account = await svc.create(
        ctx,
        AccountCreate(account_type=account_type, nickname=nickname),
    )
    await db_session.flush()
    return str(account.id)


# ── AC 0: GET /accounts/{account_id}/property endpoint ───────────────────────


async def test_get_property_by_account_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "real_estate", "Endpoint House"
    )

    # No property yet → 404
    resp = await client.get(f"/api/v1/accounts/{account_id}/property", headers=headers)
    assert resp.status_code == 404

    # Create property
    resp = await client.post(
        "/api/v1/properties",
        json={"account_id": account_id, "address": "42 Test Blvd", "property_type": "rental"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Now endpoint returns the property
    resp = await client.get(f"/api/v1/accounts/{account_id}/property", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["account_id"] == account_id
    assert body["address"] == "42 Test Blvd"
    assert body["property_type"] == "rental"


# ── AC 1: Property equity endpoint ───────────────────────────────────────────


async def test_property_equity_no_mortgage(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    # Create RE account + property
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "real_estate", "My Home"
    )
    resp = await client.post(
        "/api/v1/properties",
        json={"account_id": account_id, "address": "1 Oak St"},
        headers=headers,
    )
    assert resp.status_code == 201
    property_id = resp.json()["id"]
    assert resp.json()["property_type"] == "primary_residence"

    # No valuation → equity returns 404
    resp = await client.get(f"/api/v1/properties/{property_id}/equity", headers=headers)
    assert resp.status_code == 404

    # Add valuation
    resp = await client.post(
        f"/api/v1/properties/{property_id}/valuations",
        json={"valuation_date": "2025-06-01", "estimated_value": "500000.00"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Equity = full value, no mortgage
    resp = await client.get(f"/api/v1/properties/{property_id}/equity", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["equity"] == "500000.0000"
    assert body["mortgage_balance"] is None
    assert body["mortgage_balance_visible"] is True


async def test_property_equity_with_mortgage(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    re_id = await _make_account(
        db_session, household, primary_member, primary_user, "real_estate", "House"
    )
    mortgage_id = await _make_account(
        db_session, household, primary_member, primary_user, "mortgage", "Mortgage"
    )

    # Create property linked to mortgage
    resp = await client.post(
        "/api/v1/properties",
        json={
            "account_id": re_id,
            "address": "2 Elm St",
            "linked_mortgage_account_id": mortgage_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    property_id = resp.json()["id"]

    # Add valuation
    await client.post(
        f"/api/v1/properties/{property_id}/valuations",
        json={"valuation_date": "2025-06-01", "estimated_value": "400000.00"},
        headers=headers,
    )

    # Record the mortgage balance the way mortgages actually track it — as a
    # transaction (mortgage is transaction-based), not a snapshot. Equity reads
    # the same balance source as the Accounts ledger, so -200000 owed yields a
    # 200000 mortgage balance and 200000 equity against a 400000 valuation.
    resp = await client.post(
        f"/api/v1/accounts/{mortgage_id}/transactions",
        json={
            "transaction_date": "2025-06-01",
            "amount": "-200000.00",
            "payee_normalized": "Opening balance",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/properties/{property_id}/equity", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["equity"]) == Decimal("200000.0000")
    assert Decimal(body["mortgage_balance"]) == Decimal("200000.0000")


# ── AC 2: property_type field ─────────────────────────────────────────────────


async def test_property_type_create_and_patch(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "real_estate", "Rental"
    )

    resp = await client.post(
        "/api/v1/properties",
        json={"account_id": account_id, "address": "3 Pine St", "property_type": "rental"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["property_type"] == "rental"
    property_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/properties/{property_id}",
        json={"property_type": "vacation"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["property_type"] == "vacation"


# ── AC 3: Pension CRUD ────────────────────────────────────────────────────────


async def test_pension_crud(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "pension", "State Pension"
    )

    # 404 before creation
    resp = await client.get(f"/api/v1/accounts/{account_id}/pension", headers=headers)
    assert resp.status_code == 404

    # Create
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/pension",
        json={
            "plan_name": "PERS",
            "administrator": "State Board",
            "monthly_benefit_estimate": "2500.00",
            "eligibility_age": 62,
            "cola_adjustment_rate": "0.02",
            "is_vested": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["plan_name"] == "PERS"
    assert body["administrator"] == "State Board"
    assert body["is_vested"] is True
    assert body["monthly_benefit_estimate"] == "2500.0000"

    # GET
    resp = await client.get(f"/api/v1/accounts/{account_id}/pension", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["plan_name"] == "PERS"

    # PATCH
    resp = await client.patch(
        f"/api/v1/accounts/{account_id}/pension",
        json={"monthly_benefit_estimate": "3000.00"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["monthly_benefit_estimate"] == "3000.0000"
    assert resp.json()["plan_name"] == "PERS"  # unchanged


async def test_pension_model_fields_set_semantics(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """PATCH only updates fields that are explicitly included in the request body."""
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "pension", "PATCH Test Pension"
    )
    await client.post(
        f"/api/v1/accounts/{account_id}/pension",
        json={
            "monthly_benefit_estimate": "1000.00",
            "eligibility_age": 65,
            "cola_adjustment_rate": "0.03",
        },
        headers=headers,
    )

    # PATCH only is_vested; all other fields must remain
    resp = await client.patch(
        f"/api/v1/accounts/{account_id}/pension",
        json={"is_vested": True},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_vested"] is True
    assert body["monthly_benefit_estimate"] == "1000.0000"
    assert body["eligibility_age"] == 65
    assert Decimal(body["cola_adjustment_rate"]) == Decimal("0.0300")


async def test_pension_rbac(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    """Partner cannot access pension on primary's private account."""
    primary_headers = auth_headers(primary_user, primary_member, "primary")
    partner_headers = auth_headers(partner_user, partner_member, "partner")

    from app.core.visibility import VisibilityContext
    from app.services.account import AccountService

    ctx = VisibilityContext(
        user_id=primary_user.id,
        member_id=primary_member.id,
        role="primary",
        household_id=household.id,
    )
    svc = AccountService(db_session)
    account = await svc.create(
        ctx,
        AccountCreate(
            account_type="pension",
            nickname="Private Pension",
            owner_member_id=primary_member.id,
        ),
    )
    await db_session.flush()
    account_id = str(account.id)

    # Primary creates pension record
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/pension",
        json={"monthly_benefit_estimate": "2000.00"},
        headers=primary_headers,
    )
    assert resp.status_code == 201

    # Partner cannot see it
    resp = await client.get(f"/api/v1/accounts/{account_id}/pension", headers=partner_headers)
    assert resp.status_code == 404


# ── AC 4: FIRE detection pension streams ─────────────────────────────────────


async def test_fire_detect_includes_vested_pension_stream(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "pension", "FIRE Pension"
    )

    # Set up a vested pension with a benefit estimate
    pension = PensionAccount(
        account_id=uuid.UUID(account_id),
        is_vested=True,
        monthly_benefit_estimate=Decimal("3000.00"),
        cola_adjustment_rate=Decimal("0.025"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(pension)
    await db_session.flush()

    # Create a FIRE scenario
    resp = await client.post(
        "/api/v1/fire-scenarios",
        json={
            "name": "Test FIRE",
            "target_annual_spend": "60000.00",
            "safe_withdrawal_rate": "0.04",
            "expected_annual_return": "0.07",
            "expected_inflation_rate": "0.03",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    scenario_id = resp.json()["id"]

    # Trigger detection
    resp = await client.post(
        f"/api/v1/fire-scenarios/{scenario_id}/detect",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    # Look for a pension income stream
    pension_streams = [
        s
        for s in body["scenario"]["additional_income_streams"]
        if s["type"] == "pension" and s["auto_detected"]
    ]
    assert len(pension_streams) == 1
    assert Decimal(pension_streams[0]["amount_annual"]) == Decimal("36000.00")
    assert pension_streams[0]["source_account_id"] == account_id


async def test_fire_detect_deduplication_by_source_account(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Re-running detect on same pension → same stream preserved, amount updated."""
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "pension", "Dedup Pension"
    )
    pension = PensionAccount(
        account_id=uuid.UUID(account_id),
        is_vested=True,
        monthly_benefit_estimate=Decimal("2000.00"),
        cola_adjustment_rate=Decimal("0.02"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(pension)
    await db_session.flush()

    resp = await client.post(
        "/api/v1/fire-scenarios",
        json={
            "name": "Dedup FIRE",
            "target_annual_spend": "50000.00",
            "safe_withdrawal_rate": "0.04",
            "expected_annual_return": "0.07",
            "expected_inflation_rate": "0.03",
        },
        headers=headers,
    )
    scenario_id = resp.json()["id"]

    # First detect
    await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)

    # Second detect (e.g., benefit increased)
    pension.monthly_benefit_estimate = Decimal("2500.00")
    await db_session.flush()

    resp = await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)
    assert resp.status_code == 200
    streams = resp.json()["scenario"]["additional_income_streams"]
    pension_streams = [
        s for s in streams if s["type"] == "pension" and s["source_account_id"] == account_id
    ]
    # Should be exactly one stream, updated amount
    assert len(pension_streams) == 1
    assert Decimal(pension_streams[0]["amount_annual"]) == Decimal("30000.00")


# ── AC 5: Net worth pension annotations ──────────────────────────────────────


async def test_net_worth_pension_annotations(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _make_account(
        db_session, household, primary_member, primary_user, "pension", "NW Pension"
    )

    pension = PensionAccount(
        account_id=uuid.UUID(account_id),
        monthly_benefit_estimate=Decimal("1800.00"),
        eligibility_age=65,
        eligibility_date=date(2040, 1, 1),
        cola_adjustment_rate=Decimal("0.02"),
        is_vested=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(pension)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/reports/net-worth?from=2025-01-01&to=2025-12-31",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "pension_annotations" in body
    annotations = body["pension_annotations"]
    assert len(annotations) == 1
    assert annotations[0]["nickname"] == "NW Pension"
    assert Decimal(annotations[0]["monthly_benefit"]) == Decimal("1800")
    assert annotations[0]["eligibility_age"] == 65


# ── AC 6: FIRE detect RBAC — partner cannot see primary's private pension ────


async def test_fire_detect_partner_cannot_see_primary_private_pension(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    """Partner FIRE detect must not include pension streams from primary's private accounts."""
    partner_headers = auth_headers(partner_user, partner_member, "partner")

    # Primary creates a pension account owned by primary only (private)
    primary_ctx = VisibilityContext(
        user_id=primary_user.id,
        member_id=primary_member.id,
        role="primary",
        household_id=household.id,
    )
    svc = AccountService(db_session)
    account = await svc.create(
        primary_ctx,
        AccountCreate(
            account_type="pension",
            nickname="Primary Private Pension",
            owner_member_id=primary_member.id,
        ),
    )
    await db_session.flush()
    account_id = account.id

    pension = PensionAccount(
        account_id=uuid.UUID(str(account_id)),
        is_vested=True,
        monthly_benefit_estimate=Decimal("5000.00"),
        cola_adjustment_rate=Decimal("0.02"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(pension)
    await db_session.flush()

    # Partner creates a FIRE scenario
    resp = await client.post(
        "/api/v1/fire-scenarios",
        json={
            "name": "Partner FIRE",
            "target_annual_spend": "40000.00",
            "safe_withdrawal_rate": "0.04",
            "expected_annual_return": "0.07",
            "expected_inflation_rate": "0.03",
        },
        headers=partner_headers,
    )
    assert resp.status_code == 201
    scenario_id = resp.json()["id"]

    # Partner runs detect — must NOT see primary's private pension
    resp = await client.post(
        f"/api/v1/fire-scenarios/{scenario_id}/detect",
        headers=partner_headers,
    )
    assert resp.status_code == 200
    streams = resp.json()["scenario"]["additional_income_streams"]
    pension_streams = [s for s in streams if s["type"] == "pension"]
    # Primary's private pension should not appear for partner
    assert all(s["source_account_id"] != str(account_id) for s in pension_streams)
