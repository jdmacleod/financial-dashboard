"""Integration tests for the synchronous staging endpoint (T3) and dedupe (T4)."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core import throttle
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


@pytest.fixture(autouse=True)
def _clear_throttle() -> Any:
    throttle.reset_all()
    yield
    throttle.reset_all()


async def _account(client: AsyncClient, user: User, member: HouseholdMember) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": "Ingest Checking"},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _pat(client: AsyncClient, user: User, member: HouseholdMember) -> str:
    resp = await client.post(
        "/api/v1/personal-access-tokens",
        json={"label": "ingest"},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201
    return resp.json()["token"]


async def test_stage_rows_via_pat(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    account_id = await _account(client, primary_user, primary_member)
    token = await _pat(client, primary_user, primary_member)
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={
            "rows": [
                {
                    "transaction_date": "2026-01-05",
                    "amount": "-42.10",
                    "payee_raw": "Coffee",
                    "external_id": "x1",
                },
                {
                    "transaction_date": "2026-01-06",
                    "amount": "-9.99",
                    "payee_raw": "Music",
                    "external_id": "x2",
                },
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["staged"] == 2
    assert body["skipped_duplicate"] == 0
    assert body["failed"] == 0


async def test_staging_does_not_touch_balance(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    """The core trust guarantee: staged rows never move account balance."""
    account_id = await _account(client, primary_user, primary_member)
    headers = auth_headers(primary_user, primary_member, "primary")

    before = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()

    staged = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={
            "rows": [
                {
                    "transaction_date": "2026-02-01",
                    "amount": "50000.00",
                    "payee_raw": "Surprise",
                    "external_id": "big",
                }
            ]
        },
        headers=headers,
    )
    assert staged.status_code == 201
    assert staged.json()["staged"] == 1

    after = (await client.get(f"/api/v1/accounts/{account_id}", headers=headers)).json()
    assert after["current_balance"] == before["current_balance"]


async def test_idempotent_rebatch_skips_duplicates(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    account_id = await _account(client, primary_user, primary_member)
    headers = auth_headers(primary_user, primary_member, "primary")
    rows = {
        "rows": [
            {
                "transaction_date": "2026-03-01",
                "amount": "-5.00",
                "payee_raw": "Bus",
                "external_id": "ride-1",
            }
        ]
    }

    first = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging", json=rows, headers=headers
    )
    assert first.json()["staged"] == 1

    second = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging", json=rows, headers=headers
    )
    assert second.json()["staged"] == 0
    assert second.json()["skipped_duplicate"] == 1


async def test_server_redacts_pii_before_storing(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    account_id = await _account(client, primary_user, primary_member)
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={
            "rows": [
                {
                    "transaction_date": "2026-04-01",
                    "amount": "-1.00",
                    "memo": "ACH ACCT 4111111111111111",
                    "external_id": "pii-1",
                }
            ]
        },
        headers=headers,
    )
    batch_id = resp.json()["batch_id"]
    listed = await client.get(
        f"/api/v1/accounts/{account_id}/import/staging/{batch_id}", headers=headers
    )
    stored_memo = listed.json()[0]["memo"]
    assert "4111111111111111" not in stored_memo
    assert "1111" in stored_memo


async def test_intra_batch_duplicate_external_id(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    account_id = await _account(client, primary_user, primary_member)
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={
            "rows": [
                {"transaction_date": "2026-05-01", "amount": "-1.00", "external_id": "dup"},
                {"transaction_date": "2026-05-01", "amount": "-1.00", "external_id": "dup"},
            ]
        },
        headers=headers,
    )
    assert resp.json()["staged"] == 1
    assert resp.json()["skipped_duplicate"] == 1


async def test_partner_session_can_stage(
    client: AsyncClient,
    partner_user: User,
    partner_member: HouseholdMember,
    primary_user: User,
    primary_member: HouseholdMember,
) -> None:
    account_id = await _account(client, primary_user, primary_member)
    resp = await client.post(
        f"/api/v1/accounts/{account_id}/import/staging",
        json={"rows": [{"transaction_date": "2026-06-01", "amount": "-1.00"}]},
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 201


async def test_unknown_account_404(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        "/api/v1/accounts/00000000-0000-0000-0000-000000000000/import/staging",
        json={"rows": [{"transaction_date": "2026-06-01", "amount": "-1.00"}]},
        headers=headers,
    )
    assert resp.status_code == 404
