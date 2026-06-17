"""CRUD coverage for Phase 2 endpoints beyond the acceptance-criteria transcription
in test_phase_2.py — categories, snapshots, transaction mutation, and import job
listing/preview, none of which have a dedicated phase-2 AC of their own."""

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def _seed_category(db_session: AsyncSession, household: Household, name: str) -> Category:
    category = Category(
        household_id=household.id,
        name=name,
        is_income=False,
        is_system=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(category)
    await db_session.flush()
    return category


async def _create_account(
    client: AsyncClient, user: User, member: HouseholdMember, nickname: str
) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": nickname},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_create_and_update_category(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    create_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Groceries", "is_income": False},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert create_resp.status_code == 201
    category_id = create_resp.json()["id"]
    assert create_resp.json()["is_system"] is False

    update_resp = await client.patch(
        f"/api/v1/categories/{category_id}",
        json={"name": "Groceries & Dining"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Groceries & Dining"


async def test_update_system_category_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    system_category = Category(
        household_id=household.id,
        name="Uncategorized",
        is_income=False,
        is_system=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(system_category)
    await db_session.flush()

    resp = await client.patch(
        f"/api/v1/categories/{system_category.id}",
        json={"name": "Renamed"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 409


async def test_snapshot_crud_lifecycle(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "401k")
    headers = auth_headers(primary_user, primary_member, "primary")

    create_resp = await client.post(
        f"/api/v1/accounts/{account_id}/snapshots",
        json={"snapshot_date": "2025-01-31", "balance": "10000.00"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    snapshot_id = create_resp.json()["id"]
    assert create_resp.json()["balance"] == "10000.0000"

    list_resp = await client.get(f"/api/v1/accounts/{account_id}/snapshots", headers=headers)
    assert len(list_resp.json()) == 1

    update_resp = await client.patch(
        f"/api/v1/accounts/{account_id}/snapshots/{snapshot_id}",
        json={"balance": "10500.00", "memo": "Market gain"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["balance"] == "10500.0000"
    assert update_resp.json()["memo"] == "Market gain"

    delete_resp = await client.delete(
        f"/api/v1/accounts/{account_id}/snapshots/{snapshot_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_after_delete = await client.get(
        f"/api/v1/accounts/{account_id}/snapshots", headers=headers
    )
    assert list_after_delete.json() == []


async def test_delete_transaction(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    headers = auth_headers(primary_user, primary_member, "primary")

    create_resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2025-01-15",
            "amount": "-20.00",
            "payee_normalized": "Coffee Shop",
        },
        headers=headers,
    )
    transaction_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/transactions/{transaction_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/transactions/{transaction_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_bulk_categorize_transactions(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    headers = auth_headers(primary_user, primary_member, "primary")
    category = await _seed_category(db_session, household, "Dining")

    txn_ids = []
    for amount in ("-10.00", "-20.00"):
        resp = await client.post(
            f"/api/v1/accounts/{account_id}/transactions",
            json={
                "transaction_date": "2025-01-15",
                "amount": amount,
                "payee_normalized": "Restaurant",
            },
            headers=headers,
        )
        txn_ids.append(resp.json()["id"])

    bulk_resp = await client.patch(
        f"/api/v1/accounts/{account_id}/transactions/bulk-categorize",
        json={"transaction_ids": txn_ids, "category_id": str(category.id)},
        headers=headers,
    )
    assert bulk_resp.status_code == 200
    results = bulk_resp.json()
    assert len(results) == 2
    assert all(t["category_id"] == str(category.id) for t in results)
    assert all(t["is_reviewed"] is True for t in results)


async def test_import_preview_returns_headers_and_suggested_mapping(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    content = b"Date,Amount,Description\n2025-01-15,-84.23,WHOLEFDS #123\n"

    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/preview",
        files={"file": ("sample.csv", content, "text/csv")},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["headers"] == ["Date", "Amount", "Description"]
    assert body["suggested_mapping"]["transaction_date"] == "Date"


async def test_start_import_with_unsupported_extension_returns_400(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")

    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import",
        files={"file": ("statement.pdf", b"%PDF-1.4", "application/pdf")},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 400


async def test_list_import_jobs_scoped_to_visible_accounts(
    client: AsyncClient, primary_member: HouseholdMember, primary_user: User
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    headers = auth_headers(primary_user, primary_member, "primary")
    content = b"Date,Amount,Description\n2025-01-15,-84.23,WHOLEFDS #123\n"

    start_resp = await client.post(
        f"/api/v1/accounts/{account_id}/import",
        files={"file": ("sample.csv", content, "text/csv")},
        headers=headers,
    )
    assert start_resp.status_code == 201

    list_resp = await client.get("/api/v1/import-jobs", headers=headers)
    assert list_resp.status_code == 200
    jobs = list_resp.json()
    assert len(jobs) == 1
    assert jobs[0]["account_id"] == account_id
