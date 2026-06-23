"""User provisioning: one-action member+user create with a temporary password.

Covers POST /members/provision (RBAC, role-escalation guard, duplicate email),
the temp password being hashed at rest, the must_change_password login flag and
its clearing via change-password, and temporary-password regeneration.
"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_provision_happy_path(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(primary_user, primary_member, "primary"),
        json={"display_name": "Kiddo", "role": "dependent", "email": "kiddo@example.com"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["member"]["display_name"] == "Kiddo"
    assert body["member"]["role"] == "dependent"
    assert body["user"]["email"] == "kiddo@example.com"
    temp = body["temporary_password"]
    assert temp and len(temp) >= 16
    # The plaintext temp password is NOT echoed inside the user object.
    assert temp not in str(body["user"])

    # Stored as a bcrypt hash, never the plaintext.
    row = await db_session.execute(select(User).where(User.email == "kiddo@example.com"))
    user = row.scalar_one()
    assert user.hashed_password != temp
    assert user.hashed_password.startswith("$2")
    assert user.must_change_password is True

    # The returned temp password actually logs in, and the login flags the forced reset.
    login = await client.post(
        "/api/v1/auth/login", json={"email": "kiddo@example.com", "password": temp}
    )
    assert login.status_code == 200, login.text
    assert login.json()["must_change_password"] is True


async def test_partner_can_provision(
    client: AsyncClient,
    household: Household,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(partner_user, partner_member, "partner"),
        json={"display_name": "Guest", "role": "partner", "email": "guest@example.com"},
    )
    assert resp.status_code == 201, resp.text


async def test_dependent_cannot_provision(
    client: AsyncClient,
    household: Household,
    make_member,
    make_user,
) -> None:
    dep_member = await make_member(role="dependent", display_name="Dep")
    dep_user = await make_user(dep_member, "dep@example.com")
    resp = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(dep_user, dep_member, "dependent"),
        json={"display_name": "Nope", "role": "partner", "email": "nope@example.com"},
    )
    assert resp.status_code == 403, resp.text


async def test_partner_cannot_provision_primary(
    client: AsyncClient,
    household: Household,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    resp = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(partner_user, partner_member, "partner"),
        json={"display_name": "Boss", "role": "primary", "email": "boss@example.com"},
    )
    assert resp.status_code == 403, resp.text
    assert "primary" in resp.json()["detail"].lower()


async def test_duplicate_email_409(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # primary_user already owns primary@example.com.
    resp = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(primary_user, primary_member, "primary"),
        json={"display_name": "Dupe", "role": "partner", "email": "primary@example.com"},
    )
    assert resp.status_code == 409, resp.text


async def test_change_password_clears_must_change_flag(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    prov = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(primary_user, primary_member, "primary"),
        json={"display_name": "Newbie", "role": "partner", "email": "newbie@example.com"},
    )
    temp = prov.json()["temporary_password"]
    user_id = prov.json()["user"]["id"]
    member_id = prov.json()["member"]["id"]

    # New person logs in (forced-reset flagged) and sets their own password.
    login = await client.post(
        "/api/v1/auth/login", json={"email": "newbie@example.com", "password": temp}
    )
    token = login.json()["access_token"]
    change = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": temp,
            "new_password": "ChosenPassw0rd!",  # pragma: allowlist secret — test fixture
        },
    )
    assert change.status_code == 204, change.text

    # A fresh login no longer flags the forced reset.
    relogin = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "newbie@example.com",
            "password": "ChosenPassw0rd!",  # pragma: allowlist secret — test fixture
        },
    )
    assert relogin.status_code == 200, relogin.text
    assert relogin.json()["must_change_password"] is False

    # Regenerate is now refused — they've claimed their own password.
    regen = await client.post(
        f"/api/v1/members/users/{user_id}/temporary-password",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert regen.status_code == 409, regen.text
    assert member_id  # provisioned member exists


async def test_regenerate_temporary_password_while_unclaimed(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    prov = await client.post(
        "/api/v1/members/provision",
        headers=auth_headers(primary_user, primary_member, "primary"),
        json={"display_name": "Pending", "role": "partner", "email": "pending@example.com"},
    )
    first_temp = prov.json()["temporary_password"]
    user_id = prov.json()["user"]["id"]

    regen = await client.post(
        f"/api/v1/members/users/{user_id}/temporary-password",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert regen.status_code == 200, regen.text
    new_temp = regen.json()["temporary_password"]
    assert new_temp != first_temp

    # Old temp password no longer works; new one does.
    old = await client.post(
        "/api/v1/auth/login", json={"email": "pending@example.com", "password": first_temp}
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/v1/auth/login", json={"email": "pending@example.com", "password": new_temp}
    )
    assert new.status_code == 200, new.text
    assert new.json()["must_change_password"] is True
