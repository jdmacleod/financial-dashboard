"""Phase 2 acceptance criteria, transcribed 1:1 from docs/phase-2-transactions.md."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt
from app.db.models.audit_log import AuditLog
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.worker.tasks.import_tasks import run_import_job

from ..conftest import auth_headers

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@asynccontextmanager
async def _session_ctx(session: AsyncSession):  # type: ignore[no-untyped-def]
    yield session


async def _run_worker(
    db_session: AsyncSession,
    job_id: str,
    content: bytes,
    fmt: str,
    mapping: dict[str, str] | None,
    household_id: str,
) -> None:
    """Simulates the ARQ worker consuming the job synchronously in-test."""
    ctx = {"db": lambda: _session_ctx(db_session)}
    await run_import_job(ctx, job_id, content, fmt, mapping, household_id)


async def _seed_category(
    db_session: AsyncSession, household: Household, name: str, *, is_system: bool = False
) -> Category:
    category = Category(
        household_id=household.id,
        name=name,
        is_income=False,
        is_system=is_system,
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


async def test_csv_import_records_correct_amounts_and_dates(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    content = (FIXTURES / "chase_sample.csv").read_bytes()
    mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
        "external_id": "Reference",
    }

    start_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        data={"mapping": json.dumps(mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert start_resp.status_code == 201
    job_id = start_resp.json()["id"]

    await _run_worker(db_session, job_id, content, "csv", mapping, str(household.id))

    job_resp = await client.get(
        f"/api/v1/import-jobs/{job_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert job_resp.json()["status"] == "complete"
    assert job_resp.json()["records_found"] == 3
    assert job_resp.json()["records_imported"] == 3
    assert job_resp.json()["records_skipped"] == 0

    list_resp = await client.get(
        f"/api/v1/accounts/{checking_id}/transactions",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    items = {t["external_id"]: t for t in list_resp.json()["items"]}
    assert items["TXN-1001"]["amount"] == "-84.2300"
    assert items["TXN-1001"]["transaction_date"] == "2025-01-15"
    assert items["TXN-1002"]["amount"] == "2500.0000"


async def test_reimporting_same_csv_skips_all_as_duplicates(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    content = (FIXTURES / "chase_sample.csv").read_bytes()
    mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
        "external_id": "Reference",
    }

    first_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        data={"mapping": json.dumps(mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    first_job_id = first_resp.json()["id"]
    await _run_worker(db_session, first_job_id, content, "csv", mapping, str(household.id))

    second_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        data={"mapping": json.dumps(mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    second_job_id = second_resp.json()["id"]
    await _run_worker(db_session, second_job_id, content, "csv", mapping, str(household.id))

    job_resp = await client.get(
        f"/api/v1/import-jobs/{second_job_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert job_resp.json()["records_skipped"] == 3
    assert job_resp.json()["records_imported"] == 0
    assert job_resp.json()["status"] == "complete"


async def test_ofx_import_maps_fields_without_mapping_ui(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    content = (FIXTURES / "sample.ofx").read_bytes()

    start_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("sample.ofx", content, "application/octet-stream")},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert start_resp.status_code == 201
    job_id = start_resp.json()["id"]
    assert start_resp.json()["format"] == "ofx"

    await _run_worker(db_session, job_id, content, "ofx", None, str(household.id))

    list_resp = await client.get(
        f"/api/v1/accounts/{checking_id}/transactions",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    items = list_resp.json()["items"]
    assert len(items) == 1
    txn = items[0]
    assert txn["transaction_date"] == "2025-01-17"
    assert txn["post_date"] == "2025-01-18"
    assert txn["amount"] == "-45.1000"
    assert txn["payee_raw"] == "AMAZON.COM"
    assert txn["memo"] == "ONLINE PURCHASE"
    assert txn["external_id"] == "OFXTXN0001"


async def test_transfer_pair_auto_detected_and_linked(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    await _seed_category(db_session, household, "Transfer", is_system=True)

    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    savings_id = await _create_account(client, primary_user, primary_member, "Savings")

    checking_content = (FIXTURES / "chase_sample.csv").read_bytes()
    checking_mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
        "external_id": "Reference",
    }
    checking_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("chase_sample.csv", checking_content, "text/csv")},
        data={"mapping": json.dumps(checking_mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    await _run_worker(
        db_session,
        checking_resp.json()["id"],
        checking_content,
        "csv",
        checking_mapping,
        str(household.id),
    )

    savings_content = (FIXTURES / "savings_sample.csv").read_bytes()
    savings_resp = await client.post(
        f"/api/v1/accounts/{savings_id}/import",
        files={"file": ("savings_sample.csv", savings_content, "text/csv")},
        data={"mapping": json.dumps(checking_mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    await _run_worker(
        db_session,
        savings_resp.json()["id"],
        savings_content,
        "csv",
        checking_mapping,
        str(household.id),
    )

    checking_txns = (
        await client.get(
            f"/api/v1/accounts/{checking_id}/transactions",
            headers=auth_headers(primary_user, primary_member, "primary"),
        )
    ).json()["items"]
    savings_txns = (
        await client.get(
            f"/api/v1/accounts/{savings_id}/transactions",
            headers=auth_headers(primary_user, primary_member, "primary"),
        )
    ).json()["items"]

    transfer_leg = next(t for t in checking_txns if t["external_id"] == "TXN-1003")
    deposit_leg = next(t for t in savings_txns if t["external_id"] == "TXN-2001")

    assert transfer_leg["is_transfer"] is True
    assert deposit_leg["is_transfer"] is True
    assert transfer_leg["transfer_pair_id"] == deposit_leg["transfer_pair_id"]
    assert transfer_leg["transfer_pair_id"] is not None


async def test_patch_transaction_category_change_writes_audit_event(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    old_category = await _seed_category(db_session, household, "Groceries")
    new_category = await _seed_category(db_session, household, "Dining")

    create_resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2025-01-15",
            "amount": "-20.00",
            "payee_normalized": "Restaurant",
            "category_id": str(old_category.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert create_resp.status_code == 201
    transaction_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/transactions/{transaction_id}",
        json={"category_id": str(new_category.id)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["category_id"] == str(new_category.id)

    audit_rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.action == "transaction.category_changed",
                    AuditLog.entity_id == uuid.UUID(transaction_id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(audit_rows) == 1
    audit_row = audit_rows[0]
    assert audit_row.previous_value is not None
    assert audit_row.previous_value["category_id"] == str(old_category.id)
    assert audit_row.new_value["category_id"] == str(new_category.id)


async def test_delete_system_category_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    system_category = await _seed_category(db_session, household, "Uncategorized", is_system=True)

    resp = await client.delete(
        f"/api/v1/categories/{system_category.id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 409


async def test_delete_user_category_reassigns_transactions_to_uncategorized(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    await _seed_category(db_session, household, "Uncategorized", is_system=True)
    custom_category = await _seed_category(db_session, household, "Hobbies")
    account_id = await _create_account(client, primary_user, primary_member, "Checking")

    create_resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2025-01-15",
            "amount": "-20.00",
            "payee_normalized": "Hobby Shop",
            "category_id": str(custom_category.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    transaction_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/categories/{custom_category.id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/transactions/{transaction_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    uncategorized_resp = await client.get(
        "/api/v1/categories", headers=auth_headers(primary_user, primary_member, "primary")
    )
    uncategorized = next(
        c for c in uncategorized_resp.json() if c["name"] == "Uncategorized" and c["is_system"]
    )
    assert get_resp.json()["category_id"] == uncategorized["id"]


async def test_dependent_cannot_create_transaction(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    account_id = await _create_account(client, primary_user, primary_member, "Checking")
    dependent_member = await make_member(role="dependent")  # type: ignore[operator]
    dependent_user = await make_user(dependent_member, "dependent@example.com")  # type: ignore[operator]

    resp = await client.post(
        f"/api/v1/accounts/{account_id}/transactions",
        json={
            "transaction_date": "2025-01-15",
            "amount": "-20.00",
            "payee_normalized": "Restaurant",
        },
        headers=auth_headers(dependent_user, dependent_member, "dependent"),
    )
    assert resp.status_code == 403


async def test_transaction_with_real_estate_property_id_returned_and_filterable(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    re_account_resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "real_estate", "nickname": "Rental Property"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    re_account_id = re_account_resp.json()["id"]

    property_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO real_estate_properties "
            "(id, account_id, address_enc, created_at, updated_at) "
            "VALUES (:id, :account_id, :address_enc, now(), now())"
        ),
        {
            "id": property_id,
            "account_id": uuid.UUID(re_account_id),
            "address_enc": encrypt("123 Main St"),
        },
    )

    checking_id = await _create_account(client, primary_user, primary_member, "Checking")

    with_property = await client.post(
        f"/api/v1/accounts/{checking_id}/transactions",
        json={
            "transaction_date": "2025-01-15",
            "amount": "-150.00",
            "payee_normalized": "Roof Repair",
            "real_estate_property_id": str(property_id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert with_property.status_code == 201
    assert with_property.json()["real_estate_property_id"] == str(property_id)

    without_property = await client.post(
        f"/api/v1/accounts/{checking_id}/transactions",
        json={
            "transaction_date": "2025-01-16",
            "amount": "-10.00",
            "payee_normalized": "Coffee",
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert without_property.status_code == 201

    filtered_resp = await client.get(
        f"/api/v1/accounts/{checking_id}/transactions",
        params={"real_estate_property_id": str(property_id)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    items = filtered_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["real_estate_property_id"] == str(property_id)


async def test_import_job_status_complete_with_correct_counts(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    content = (FIXTURES / "chase_sample.csv").read_bytes()
    mapping = {
        "transaction_date": "Date",
        "amount": "Amount",
        "payee_raw": "Description",
        "external_id": "Reference",
    }

    start_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/import",
        files={"file": ("chase_sample.csv", content, "text/csv")},
        data={"mapping": json.dumps(mapping)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    job_id = start_resp.json()["id"]
    assert start_resp.json()["status"] == "pending"

    await _run_worker(db_session, job_id, content, "csv", mapping, str(household.id))

    job_resp = await client.get(
        f"/api/v1/import-jobs/{job_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    body = job_resp.json()
    assert body["status"] == "complete"
    assert body["records_found"] == 3
    assert body["records_imported"] == 3
    assert body["records_skipped"] == 0
