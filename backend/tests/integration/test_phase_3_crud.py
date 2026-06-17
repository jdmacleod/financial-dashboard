"""CRUD coverage for Phase 3 budget and property endpoints."""

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def _seed_category(db_session: AsyncSession, household: Household, name: str) -> Category:
    category = Category(
        household_id=household.id, name=name, is_income=False, is_system=False, created_at=_now()
    )
    db_session.add(category)
    await db_session.flush()
    return category


async def _create_account(
    client: AsyncClient, user: User, member: HouseholdMember, nickname: str, account_type: str
) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": account_type, "nickname": nickname},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_budget_crud_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    category = await _seed_category(db_session, household, "Groceries")

    create_resp = await client.post(
        "/api/v1/budgets",
        json={
            "category_id": str(category.id),
            "period": "monthly",
            "amount": "400.00",
            "effective_from": "2025-01-01",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    budget_id = create_resp.json()["id"]
    assert create_resp.json()["amount"] == "400.00"

    list_resp = await client.get("/api/v1/budgets", headers=headers)
    assert len(list_resp.json()) == 1

    update_resp = await client.patch(
        f"/api/v1/budgets/{budget_id}", json={"amount": "450.00"}, headers=headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["amount"] == "450.00"

    delete_resp = await client.delete(f"/api/v1/budgets/{budget_id}", headers=headers)
    assert delete_resp.status_code == 204

    list_after = await client.get("/api/v1/budgets", headers=headers)
    assert list_after.json() == []


async def test_budget_audit_log_records_create_update_delete(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    category = await _seed_category(db_session, household, "Dining")

    create_resp = await client.post(
        "/api/v1/budgets",
        json={
            "category_id": str(category.id),
            "period": "monthly",
            "amount": "200.00",
            "effective_from": "2025-01-01",
        },
        headers=headers,
    )
    budget_id = create_resp.json()["id"]

    await client.patch(f"/api/v1/budgets/{budget_id}", json={"amount": "250.00"}, headers=headers)
    await client.delete(f"/api/v1/budgets/{budget_id}", headers=headers)

    resp = await db_session.execute(
        AuditLog.__table__.select().where(AuditLog.entity_id == budget_id)
    )
    rows = resp.fetchall()
    actions = {row.action for row in rows}
    assert actions == {"budget.created", "budget.updated", "budget.deleted"}


async def test_property_create_rejects_non_real_estate_account(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )

    resp = await client.post(
        "/api/v1/properties",
        json={"account_id": checking_id, "address": "1 Bad St"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_property_create_rejects_duplicate_for_same_account(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    property_account_id = await _create_account(
        client, primary_user, primary_member, "Rental", "real_estate"
    )

    first = await client.post(
        "/api/v1/properties",
        json={"account_id": property_account_id, "address": "1 Main St"},
        headers=headers,
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/properties",
        json={"account_id": property_account_id, "address": "1 Main St"},
        headers=headers,
    )
    assert second.status_code == 409


async def test_property_address_is_never_plaintext_in_audit_log(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    property_account_id = await _create_account(
        client, primary_user, primary_member, "Rental", "real_estate"
    )

    create_resp = await client.post(
        "/api/v1/properties",
        json={"account_id": property_account_id, "address": "42 Secret Ave"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    property_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/properties/{property_id}",
        json={"address": "99 New Address Blvd"},
        headers=headers,
    )
    assert update_resp.status_code == 200

    resp = await db_session.execute(
        AuditLog.__table__.select().where(AuditLog.entity_id == property_id)
    )
    rows = resp.fetchall()
    assert len(rows) >= 2
    for row in rows:
        for blob in (row.previous_value, row.new_value):
            if blob is None:
                continue
            assert "address_enc" not in blob
            serialized = str(blob)
            assert "Secret Ave" not in serialized
            assert "New Address Blvd" not in serialized


async def test_property_valuation_lifecycle(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    property_account_id = await _create_account(
        client, primary_user, primary_member, "Rental", "real_estate"
    )
    create_resp = await client.post(
        "/api/v1/properties",
        json={"account_id": property_account_id, "address": "1 Main St"},
        headers=headers,
    )
    property_id = create_resp.json()["id"]

    valuation_resp = await client.post(
        f"/api/v1/properties/{property_id}/valuations",
        json={"valuation_date": "2025-06-01", "estimated_value": "350000.00", "source": "manual"},
        headers=headers,
    )
    assert valuation_resp.status_code == 201, valuation_resp.text

    list_resp = await client.get(f"/api/v1/properties/{property_id}/valuations", headers=headers)
    assert len(list_resp.json()) == 1

    get_resp = await client.get(f"/api/v1/properties/{property_id}", headers=headers)
    assert get_resp.json()["current_estimated_value"] == "350000.0000"
