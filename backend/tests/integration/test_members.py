from httpx import AsyncClient

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_primary_can_create_member(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    resp = await client.post(
        "/api/v1/members",
        json={"display_name": "New Member", "role": "partner"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 201
    assert resp.json()["display_name"] == "New Member"


async def test_partner_cannot_create_member(
    client: AsyncClient,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")

    resp = await client.post(
        "/api/v1/members",
        json={"display_name": "New Member", "role": "partner"},
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 403


async def test_list_members_returns_household_members(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    await make_member(role="partner", display_name="Other")
    resp = await client.get(
        "/api/v1/members", headers=auth_headers(primary_user, primary_member, "primary")
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_primary_can_update_member(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    target = await make_member(role="partner")
    resp = await client.patch(
        f"/api/v1/members/{target.id}",
        json={"display_name": "Renamed"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Renamed"


async def test_partner_cannot_update_member(
    client: AsyncClient,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other = await make_member(role="partner", display_name="Other")

    resp = await client.patch(
        f"/api/v1/members/{other.id}",
        json={"display_name": "Hacked"},
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 403


async def test_primary_can_deactivate_member(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    target = await make_member(role="partner")
    resp = await client.delete(
        f"/api/v1/members/{target.id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 204


async def test_partner_cannot_deactivate_member(
    client: AsyncClient,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other = await make_member(role="partner", display_name="Other")

    resp = await client.delete(
        f"/api/v1/members/{other.id}",
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 403
