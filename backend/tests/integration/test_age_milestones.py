"""Integration coverage for GET /reports/age-milestones."""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_age_milestones_lists_member_events(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = date(1990, 6, 15)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/reports/age-milestones",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    members = resp.json()["members"]
    assert len(members) == 1
    row = members[0]
    assert row["note"] is None
    keys = [m["key"] for m in row["milestones"]]
    assert keys == [
        "early_withdrawal",
        "social_security_earliest",
        "medicare",
        "full_retirement_age",
        "rmd",
    ]
    # A 1990 birthdate means every milestone is still in the future.
    assert all(m["reached"] is False for m in row["milestones"])


async def test_age_milestones_prompts_when_no_dob(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = None
    await db_session.flush()

    resp = await client.get(
        "/api/v1/reports/age-milestones",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    row = resp.json()["members"][0]
    assert row["milestones"] == []
    assert "date of birth" in row["note"].lower()
