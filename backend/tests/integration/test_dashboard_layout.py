"""Integration tests for dashboard layout endpoint."""

from __future__ import annotations

from httpx import AsyncClient

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_update_dashboard_layout_saves_widgets(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        f"/api/v1/members/{primary_member.id}/dashboard-layout",
        json={
            "widgets": [
                {"id": "metric_cards", "visible": True, "order": 0},
                {"id": "net_worth_chart", "visible": False, "order": 1},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    widgets = data["settings"]["dashboard_widgets"]
    assert len(widgets) == 2
    hidden = next(w for w in widgets if w["id"] == "net_worth_chart")
    assert hidden["visible"] is False


async def test_update_dashboard_layout_forbidden_for_other_member(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    # Partner tries to update primary's layout
    headers = auth_headers(partner_user, partner_member, "partner")
    resp = await client.patch(
        f"/api/v1/members/{primary_member.id}/dashboard-layout",
        json={"widgets": [{"id": "metric_cards", "visible": True, "order": 0}]},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_update_dashboard_layout_not_found_for_other_household(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    import uuid

    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.patch(
        f"/api/v1/members/{uuid.uuid4()}/dashboard-layout",
        json={"widgets": [{"id": "metric_cards", "visible": True, "order": 0}]},
        headers=headers,
    )
    assert resp.status_code == 404
