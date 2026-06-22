"""Write-API (CRUD) endpoints for the demo-data extension tables (Option C).

Covers create/update/delete round-trips for ownership entities, advisory notes,
insurance policies, equity grants, investment lots, and capital commitments,
plus RBAC (dependents cannot write), encrypted-field round-trips, and the
advisory-note account-visibility refinement.
"""

from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def _account(
    db_session: AsyncSession,
    household: Household,
    account_type: str = "investment_brokerage",
    *,
    owner_member_id=None,
) -> Account:
    acct = Account(
        household_id=household.id,
        account_type=account_type,
        nickname=account_type,
        include_in_net_worth=True,
        is_active=True,
        owner_member_id=owner_member_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


# --- ownership entities ------------------------------------------------------


async def test_ownership_entity_crud(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    resp = await client.post(
        "/api/v1/ownership-entities",
        headers=headers,
        json={
            "entity_type": "revocable_trust",
            "name": "Castellano Family Trust",
            "is_in_taxable_estate": True,
            "counts_in_personal_net_worth": True,
        },
    )
    assert resp.status_code == 201, resp.text
    entity = resp.json()
    assert entity["name"] == "Castellano Family Trust"
    assert "name_enc" not in entity
    entity_id = entity["id"]

    resp = await client.patch(
        f"/api/v1/ownership-entities/{entity_id}",
        headers=headers,
        json={"name": "Castellano Revocable Trust", "is_in_taxable_estate": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Castellano Revocable Trust"
    assert resp.json()["is_in_taxable_estate"] is False

    resp = await client.delete(f"/api/v1/ownership-entities/{entity_id}", headers=headers)
    assert resp.status_code == 204, resp.text

    resp = await client.get("/api/v1/ownership-entities", headers=headers)
    assert all(e["id"] != entity_id for e in resp.json())

    # The encrypted name must never have been written to the audit log.
    rows = (await db_session.execute(select(AuditLog))).scalars().all()
    actions = {r.action for r in rows}
    assert {"ownership_entity.created", "ownership_entity.updated", "ownership_entity.deleted"} <= (
        actions
    )
    for r in rows:
        for blob in (r.previous_value, r.new_value):
            assert blob is None or "name_enc" not in blob


async def test_ownership_entity_write_forbidden_for_dependent(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    make_member,
    make_user,
    primary_member: HouseholdMember,
) -> None:
    dep_member = await make_member(role="dependent", display_name="Dependent")
    dep_user = await make_user(dep_member, "dep@example.com")
    resp = await client.post(
        "/api/v1/ownership-entities",
        headers=auth_headers(dep_user, dep_member, "dependent"),
        json={"entity_type": "ilit", "name": "Nope"},
    )
    assert resp.status_code == 403, resp.text


# --- advisory notes ----------------------------------------------------------


async def test_advisory_note_crud(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    resp = await client.post(
        "/api/v1/advisory-notes",
        headers=headers,
        json={"category": "estate", "title": "NY estate cliff", "body": "Watch the threshold."},
    )
    assert resp.status_code == 201, resp.text
    note_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/advisory-notes/{note_id}",
        headers=headers,
        json={"category": "tax", "title": "Updated"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["category"] == "tax"
    assert resp.json()["title"] == "Updated"

    resp = await client.delete(f"/api/v1/advisory-notes/{note_id}", headers=headers)
    assert resp.status_code == 204, resp.text


async def test_advisory_note_account_visibility_refinement(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    make_member,
    make_user,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A note anchored to an account the dependent cannot see is hidden from
    them; a household-level note remains visible.
    """
    # Account owned by the primary → not visible to a dependent.
    private_acct = await _account(db_session, household, owner_member_id=primary_member.id)
    primary_headers = auth_headers(primary_user, primary_member, "primary")

    await client.post(
        "/api/v1/advisory-notes",
        headers=primary_headers,
        json={
            "account_id": str(private_acct.id),
            "category": "concentration",
            "title": "Private-account note",
            "body": "Anchored to the primary's account.",
        },
    )
    await client.post(
        "/api/v1/advisory-notes",
        headers=primary_headers,
        json={"category": "estate", "title": "Household note", "body": "Everyone sees this."},
    )

    dep_member = await make_member(role="dependent", display_name="Dependent")
    dep_user = await make_user(dep_member, "dep2@example.com")
    resp = await client.get(
        "/api/v1/advisory-notes", headers=auth_headers(dep_user, dep_member, "dependent")
    )
    assert resp.status_code == 200, resp.text
    titles = {n["title"] for n in resp.json()}
    assert "Household note" in titles
    assert "Private-account note" not in titles


# --- insurance policies ------------------------------------------------------


async def test_insurance_policy_crud(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    resp = await client.post(
        "/api/v1/insurance-policies",
        headers=headers,
        json={
            "policy_type": "umbrella_liability",
            "coverage_amount": "5000000",
            "premium_amount": "1200",
            "premium_cadence": "annual",
            "metadata": {"carrier": "Chubb"},
        },
    )
    assert resp.status_code == 201, resp.text
    policy = resp.json()
    assert policy["metadata"] == {"carrier": "Chubb"}
    policy_id = policy["id"]

    resp = await client.patch(
        f"/api/v1/insurance-policies/{policy_id}",
        headers=headers,
        json={"coverage_amount": "10000000"},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["coverage_amount"]) == Decimal("10000000")

    resp = await client.delete(f"/api/v1/insurance-policies/{policy_id}", headers=headers)
    assert resp.status_code == 204, resp.text


# --- equity grants -----------------------------------------------------------


async def test_equity_grant_crud(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    resp = await client.post(
        "/api/v1/equity-grants",
        headers=headers,
        json={
            "member_id": str(primary_member.id),
            "grant_type": "rsu",
            "grant_date": "2024-01-15",
            "shares_granted": "1000",
            "ticker": "ACME",
            "vesting_schedule": {"cliff_months": 12, "total_months": 48},
        },
    )
    assert resp.status_code == 201, resp.text
    grant = resp.json()
    assert grant["vesting_events"] == []
    grant_id = grant["id"]

    resp = await client.patch(
        f"/api/v1/equity-grants/{grant_id}",
        headers=headers,
        json={"shares_granted": "1200"},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["shares_granted"]) == Decimal("1200")

    resp = await client.delete(f"/api/v1/equity-grants/{grant_id}", headers=headers)
    assert resp.status_code == 204, resp.text


# --- investment lots ---------------------------------------------------------


async def test_investment_lot_crud(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    acct = await _account(db_session, household)

    resp = await client.post(
        "/api/v1/investment-lots",
        headers=headers,
        json={
            "account_id": str(acct.id),
            "ticker": "ACME",
            "shares": "100",
            "basis_per_share": "42.50",
            "acquired_date": "2023-06-01",
            "basis_type": "purchase",
        },
    )
    assert resp.status_code == 201, resp.text
    lot_id = resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/investment-lots/{lot_id}",
        headers=headers,
        json={"shares": "150", "basis_type": "rsu_vest"},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["shares"]) == Decimal("150")
    assert resp.json()["basis_type"] == "rsu_vest"

    resp = await client.delete(f"/api/v1/investment-lots/{lot_id}", headers=headers)
    assert resp.status_code == 204, resp.text


# --- capital commitments -----------------------------------------------------


async def test_capital_commitment_crud(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    nav = await _account(db_session, household, "private_fund")

    resp = await client.post(
        "/api/v1/capital-commitments",
        headers=headers,
        json={
            "fund_name": "Sequoia Capital Fund XX",
            "committed_amount": "2000000",
            "nav_account_id": str(nav.id),
            "vintage_year": 2022,
        },
    )
    assert resp.status_code == 201, resp.text
    commitment = resp.json()
    assert commitment["fund_name"] == "Sequoia Capital Fund XX"
    assert "fund_name_enc" not in commitment
    commitment_id = commitment["id"]

    resp = await client.patch(
        f"/api/v1/capital-commitments/{commitment_id}",
        headers=headers,
        json={"committed_amount": "2500000"},
    )
    assert resp.status_code == 200, resp.text
    assert Decimal(resp.json()["committed_amount"]) == Decimal("2500000")
    # fund_name still decrypts correctly after an unrelated update.
    assert resp.json()["fund_name"] == "Sequoia Capital Fund XX"

    resp = await client.delete(f"/api/v1/capital-commitments/{commitment_id}", headers=headers)
    assert resp.status_code == 204, resp.text
