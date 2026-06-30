"""Integration tests for personal access tokens (T1) and the shared
JWT-or-PAT visibility resolver (T2)."""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core import throttle
from app.core.security import create_access_token
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


@pytest.fixture(autouse=True)
def _clear_throttle() -> Any:
    throttle.reset_all()
    yield
    throttle.reset_all()


async def _create_pat(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember, label: str = "CLI"
) -> dict[str, Any]:
    resp = await client.post(
        "/api/v1/personal-access-tokens",
        json={"label": label},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_returns_token_once_then_listed_without_secret(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    created = await _create_pat(client, primary_user, primary_member)
    assert created["token"].startswith("hl_pat_")
    assert created["capability"] == "import-write"
    assert created["expires_at"] is not None

    listed = await client.get(
        "/api/v1/personal-access-tokens",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert "token" not in rows[0]  # secret never re-served
    assert rows[0]["prefix"] == created["prefix"]


async def test_partner_cannot_mint(
    client: AsyncClient, partner_user: User, partner_member: HouseholdMember
) -> None:
    resp = await client.post(
        "/api/v1/personal-access-tokens",
        json={"label": "nope"},
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 403


async def test_pat_authenticates_a_general_endpoint(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    token = (await _create_pat(client, primary_user, primary_member))["token"]
    resp = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


async def test_pat_cannot_mint_or_revoke_tokens(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    # A PAT must never reach the session-only management surface (no escalation).
    token = (await _create_pat(client, primary_user, primary_member))["token"]
    resp = await client.post(
        "/api/v1/personal-access-tokens",
        json={"label": "escalate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


async def test_revoke_then_use_is_rejected(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    created = await _create_pat(client, primary_user, primary_member)
    token = created["token"]
    headers = auth_headers(primary_user, primary_member, "primary")

    # Token works before revoke.
    ok = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200

    revoke = await client.delete(f"/api/v1/personal-access-tokens/{created['id']}", headers=headers)
    assert revoke.status_code == 204

    # Live revocation: next call fails immediately.
    after = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert after.status_code == 401


async def test_double_revoke_conflicts(
    client: AsyncClient, primary_user: User, primary_member: HouseholdMember
) -> None:
    created = await _create_pat(client, primary_user, primary_member)
    headers = auth_headers(primary_user, primary_member, "primary")
    first = await client.delete(f"/api/v1/personal-access-tokens/{created['id']}", headers=headers)
    assert first.status_code == 204
    second = await client.delete(f"/api/v1/personal-access-tokens/{created['id']}", headers=headers)
    assert second.status_code == 409


async def test_unknown_pat_rejected(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/accounts",
        headers={"Authorization": "Bearer hl_pat_deadbeef.totallyfake"},
    )
    assert resp.status_code == 401


async def test_pat_dies_when_owner_deactivated(
    client: AsyncClient,
    db_session: Any,
    primary_user: User,
    primary_member: HouseholdMember,
) -> None:
    token = (await _create_pat(client, primary_user, primary_member))["token"]
    primary_user.is_active = False
    await db_session.flush()
    resp = await client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_jwt_role_is_db_derived_not_payload(
    client: AsyncClient,
    household: Household,
    partner_user: User,
    partner_member: HouseholdMember,
) -> None:
    # Forge a token claiming 'primary' though the member is a partner in the DB.
    forged = create_access_token(str(partner_user.id), str(partner_member.id), "primary")
    resp = await client.post(
        "/api/v1/personal-access-tokens",
        json={"label": "via-forged-role"},
        headers={"Authorization": f"Bearer {forged}"},
    )
    # Resolver reads role from the DB (partner) → minting is rejected.
    assert resp.status_code == 403
