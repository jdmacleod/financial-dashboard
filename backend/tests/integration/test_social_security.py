"""Integration tests for the Social Security claiming-age estimate endpoint."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_social_security_estimate_fra_67(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = date(1960, 1, 1)  # FRA 67
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/members/{primary_member.id}/social-security-estimate",
        params={"monthly_benefit_at_fra": "2000"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fra_months"] == 804
    assert len(data["options"]) == 9
    by_age = {o["claiming_age"]: o for o in data["options"]}
    assert by_age[62]["monthly_benefit"] == "1400.00"
    assert by_age[67]["is_fra"] is True
    assert by_age[67]["monthly_benefit"] == "2000.00"
    assert by_age[70]["monthly_benefit"] == "2480.00"


async def test_social_security_estimate_requires_dob(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = None
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/members/{primary_member.id}/social-security-estimate",
        params={"monthly_benefit_at_fra": "2000"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 400


async def test_social_security_estimate_rejects_negative_benefit(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = date(1960, 1, 1)
    await db_session.flush()

    resp = await client.get(
        f"/api/v1/members/{primary_member.id}/social-security-estimate",
        params={"monthly_benefit_at_fra": "-100"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 422
