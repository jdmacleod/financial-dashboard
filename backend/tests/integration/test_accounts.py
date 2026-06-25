from httpx import AsyncClient

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_create_and_get_account(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": "checking",
            "nickname": "Chase Checking",
            "institution_name": "Chase Bank",
            "account_number": "1234567890",
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]
    assert create_resp.json()["account_number_last4"] == "7890"

    get_resp = await client.get(
        f"/api/v1/accounts/{account_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert get_resp.status_code == 200


async def test_update_account(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    create_resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": "Chase Checking"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    account_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"nickname": "Renamed"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["nickname"] == "Renamed"


async def test_tax_treatment_seeded_and_overridable(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    create_resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "retirement_401k", "nickname": "My 401k"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    account_id = create_resp.json()["id"]
    # Seeded from the account type.
    assert create_resp.json()["tax_treatment"] == "pretax"

    # Correct it to roth (e.g. an after-tax 401k).
    update_resp = await client.patch(
        f"/api/v1/accounts/{account_id}",
        json={"tax_treatment": "roth"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["tax_treatment"] == "roth"


async def test_deactivate_account(
    client: AsyncClient, household: Household, primary_member: HouseholdMember, primary_user: User
) -> None:
    create_resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": "checking", "nickname": "Chase Checking"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    account_id = create_resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/accounts/{account_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 204


async def test_partner_list_accounts_does_not_include_other_members_account(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other_member = await make_member(role="partner", display_name="Other")

    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": "checking",
            "nickname": "Others Checking",
            "owner_member_id": str(other_member.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    others_account_id = create_resp.json()["id"]

    list_resp = await client.get(
        "/api/v1/accounts", headers=auth_headers(partner_user, partner_member, "partner")
    )
    assert list_resp.status_code == 200
    visible_ids = {a["id"] for a in list_resp.json()}
    assert others_account_id not in visible_ids


async def test_partner_get_invisible_account_returns_404(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")
    other_member = await make_member(role="partner", display_name="Other")

    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": "checking",
            "nickname": "Others Checking",
            "owner_member_id": str(other_member.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    others_account_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/v1/accounts/{others_account_id}",
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert get_resp.status_code == 404


async def test_create_list_and_revoke_grant(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner_member = await make_member(role="partner")
    await make_user(owner_member, "owner@example.com")
    grantee_member = await make_member(role="partner", display_name="Grantee")

    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": "checking",
            "nickname": "Owned",
            "owner_member_id": str(owner_member.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    account_id = create_resp.json()["id"]

    grant_resp = await client.post(
        f"/api/v1/accounts/{account_id}/grants",
        json={"grantee_member_id": str(grantee_member.id)},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert grant_resp.status_code == 201
    grant_id = grant_resp.json()["id"]

    list_resp = await client.get(
        f"/api/v1/accounts/{account_id}/grants",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert any(g["id"] == grant_id for g in list_resp.json())

    revoke_resp = await client.delete(
        f"/api/v1/accounts/{account_id}/grants/{grant_id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert revoke_resp.status_code == 204

    list_after_resp = await client.get(
        f"/api/v1/accounts/{account_id}/grants",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert all(g["id"] != grant_id for g in list_after_resp.json())


async def test_partner_cannot_create_grant(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    owner_member = await make_member(role="partner")
    owner_user = await make_user(owner_member, "owner@example.com")
    grantee_member = await make_member(role="partner", display_name="Grantee")

    create_resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": "checking",
            "nickname": "Owned",
            "owner_member_id": str(owner_member.id),
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    account_id = create_resp.json()["id"]

    grant_resp = await client.post(
        f"/api/v1/accounts/{account_id}/grants",
        json={"grantee_member_id": str(grantee_member.id)},
        headers=auth_headers(owner_user, owner_member, "partner"),
    )
    assert grant_resp.status_code == 403
