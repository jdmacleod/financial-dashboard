"""Integration tests for household identity attributes (filing_status, state)."""

from __future__ import annotations

from httpx import AsyncClient

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_set_filing_status_and_state(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        "/api/v1/household",
        json={"filing_status": "married_filing_jointly", "state": "ny"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["filing_status"] == "married_filing_jointly"
    # State is normalized to uppercase.
    assert data["state"] == "NY"

    # GET reflects the persisted values.
    get_resp = await client.get("/api/v1/household", headers=headers)
    assert get_resp.json()["filing_status"] == "married_filing_jointly"
    assert get_resp.json()["state"] == "NY"


async def test_invalid_state_rejected(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        "/api/v1/household",
        json={"state": "ZZ"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_invalid_filing_status_rejected(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        "/api/v1/household",
        json={"filing_status": "married"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_clear_filing_status_and_state(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    await client.patch(
        "/api/v1/household",
        json={"filing_status": "single", "state": "CA"},
        headers=headers,
    )
    # Explicit nulls clear the fields (model_fields_set path).
    resp = await client.patch(
        "/api/v1/household",
        json={"filing_status": None, "state": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["filing_status"] is None
    assert resp.json()["state"] is None


async def test_partial_update_preserves_other_field(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    await client.patch(
        "/api/v1/household",
        json={"filing_status": "head_of_household", "state": "TX"},
        headers=headers,
    )
    # Updating only state must leave filing_status untouched.
    resp = await client.patch("/api/v1/household", json={"state": "FL"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "FL"
    assert resp.json()["filing_status"] == "head_of_household"


async def test_non_primary_cannot_update(
    client: AsyncClient,
    household: Household,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    headers = auth_headers(partner_user, partner_member, "partner")
    resp = await client.patch(
        "/api/v1/household",
        json={"filing_status": "single"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_set_and_clear_amt_preferences(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        "/api/v1/household",
        json={"amt_salt_preference": "40000.00", "amt_iso_preference": "150000"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["amt_salt_preference"] == "40000.0000"
    assert data["amt_iso_preference"] == "150000.0000"

    # Explicit nulls clear them (model_fields_set path); state is untouched.
    resp = await client.patch(
        "/api/v1/household",
        json={"amt_salt_preference": None, "amt_iso_preference": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amt_salt_preference"] is None
    assert resp.json()["amt_iso_preference"] is None


async def test_negative_amt_preference_rejected(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        "/api/v1/household",
        json={"amt_salt_preference": "-1"},
        headers=headers,
    )
    assert resp.status_code == 422
