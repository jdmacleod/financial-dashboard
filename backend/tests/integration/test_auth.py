from httpx import AsyncClient

from app.core.config import settings
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User


async def test_login_success_sets_refresh_cookie_and_returns_access_token(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.cookies


async def test_login_wrong_password_returns_401(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "wrong",  # pragma: allowlist secret
        },
    )
    assert resp.status_code == 401


async def test_refresh_rotates_token_via_cookie(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    assert login_resp.status_code == 200

    refresh_resp = await client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_logout_requires_auth_and_clears_cookie(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 204


async def test_logout_without_token_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 401


async def test_reauth_success_returns_reauth_token(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/reauth",
        json={"password": "CorrectHorse123!"},  # pragma: allowlist secret
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    assert "reauth_token" in resp.json()


async def test_reauth_wrong_password_returns_401(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    access_token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/reauth",
        json={"password": "wrong"},  # pragma: allowlist secret
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 401


async def test_login_locks_account_after_max_attempts(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    for _ in range(settings.max_login_attempts):
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": primary_user.email,
                "password": "wrong",  # pragma: allowlist secret
            },
        )
        assert resp.status_code == 401

    locked_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": primary_user.email,
            "password": "CorrectHorse123!",  # pragma: allowlist secret
        },
    )
    assert locked_resp.status_code == 423
