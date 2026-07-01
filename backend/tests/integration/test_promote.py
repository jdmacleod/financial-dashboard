"""Integration tests for promote-on-review (T5)."""

from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core import throttle
from app.db.models.audit_log import AuditLog
from app.db.models.member import HouseholdMember
from app.db.models.staging_transaction import StagingTransaction
from app.db.models.transaction import Transaction
from app.db.models.user import User

from ..conftest import auth_headers


@pytest.fixture(autouse=True)
def _clear_throttle() -> Any:
    throttle.reset_all()
    yield
    throttle.reset_all()


async def _account(client: AsyncClient, user: User, member: HouseholdMember, nick: str) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": nick},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _stage(
    client: AsyncClient, headers: dict[str, str], account_id: str, rows: list[dict[str, Any]]
) -> str:
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging", json={"rows": rows}, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["batch_id"]


async def test_promote_updates_balance_and_clears_staging(
    client: AsyncClient, db_session: Any, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _account(client, primary_user, primary_member, "Promote A")

    before = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    before_balance = Decimal(before["current_balance"] or "0")

    batch_id = await _stage(
        client,
        headers,
        account_id,
        [
            {
                "transaction_date": "2026-01-10",
                "amount": "-25.00",
                "payee_raw": "Lunch",
                "external_id": "p1",
            },
        ],
    )

    # Still staged → balance unchanged.
    mid = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    assert Decimal(mid["current_balance"] or "0") == before_balance

    promote = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}/promote", headers=headers
    )
    assert promote.status_code == 200
    assert promote.json()["promoted"] == 1

    # Now it counts in the balance, and the staging batch is empty.
    after = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    assert Decimal(after["current_balance"]) == before_balance - Decimal("25.00")

    staged_left = await db_session.execute(
        select(func.count())
        .select_from(StagingTransaction)
        .where(StagingTransaction.batch_id == batch_id)
    )
    assert staged_left.scalar_one() == 0


async def test_promote_writes_one_audit_row_per_transaction(
    client: AsyncClient, db_session: Any, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    account_id = await _account(client, primary_user, primary_member, "Promote B")
    batch_id = await _stage(
        client,
        headers,
        account_id,
        [
            {"transaction_date": "2026-02-01", "amount": "-1.00", "external_id": "a1"},
            {"transaction_date": "2026-02-02", "amount": "-2.00", "external_id": "a2"},
            {"transaction_date": "2026-02-03", "amount": "-3.00", "external_id": "a3"},
        ],
    )
    await client.post(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}/promote", headers=headers
    )
    rows = await db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.action == "transaction.created")
    )
    assert rows.scalar_one() == 3


async def test_promote_pairs_cross_account_transfer(
    client: AsyncClient, db_session: Any, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    acct_a = await _account(client, primary_user, primary_member, "Checking")
    acct_b = await _account(client, primary_user, primary_member, "Savings")

    batch_a = await _stage(
        client,
        headers,
        acct_a,
        [
            {
                "transaction_date": "2026-03-15",
                "amount": "-500.00",
                "payee_raw": "Transfer out",
                "external_id": "t-out",
            },
        ],
    )
    await client.post(
        f"/api/v1/accounts/{acct_a}/import/staging/{batch_a}/promote", headers=headers
    )
    batch_b = await _stage(
        client,
        headers,
        acct_b,
        [
            {
                "transaction_date": "2026-03-16",
                "amount": "500.00",
                "payee_raw": "Transfer in",
                "external_id": "t-in",
            },
        ],
    )
    await client.post(
        f"/api/v1/accounts/{acct_b}/import/staging/{batch_b}/promote", headers=headers
    )

    paired = await db_session.execute(
        select(func.count()).select_from(Transaction).where(Transaction.is_transfer.is_(True))
    )
    assert paired.scalar_one() == 2
    audited = await db_session.execute(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.action == "transaction.transfer_paired")
    )
    assert audited.scalar_one() == 2


async def test_promote_unknown_account_404(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        "/api/v1/accounts/00000000-0000-0000-0000-000000000000/import/staging/"
        "00000000-0000-0000-0000-000000000000/promote",
        headers=headers,
    )
    assert resp.status_code == 404
