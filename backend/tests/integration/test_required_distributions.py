"""Integration coverage for GET /reports/required-distributions."""

from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def test_required_distributions_endpoint_computes_rmd(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    primary_member.date_of_birth = date(1950, 1, 1)  # RMD age reached
    account = Account(
        household_id=primary_member.household_id,
        owner_member_id=primary_member.id,
        account_type="retirement_401k",
        nickname="401k",
        tax_treatment="pretax",
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        AccountSnapshot(
            account_id=account.id,
            snapshot_date=date(2023, 12, 31),
            balance=Decimal("1000000"),
            source="manual",
            created_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/reports/required-distributions?year=2024",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["year"] == 2024
    assert len(body["members"]) == 1
    row = body["members"][0]
    assert row["has_started"] is True
    assert row["divisor"] == "25.5"
    assert row["rmd_amount"] == "39215.69"


async def test_required_distributions_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/reports/required-distributions")
    assert resp.status_code == 401
