from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def _audit_row(db_session: AsyncSession, action: str) -> AuditLog:
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )
    return result.scalars().first()


async def test_create_user_writes_audit_row_excluding_hashed_password(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
) -> None:
    target_member = await make_member(role="partner")
    resp = await client.post(
        "/api/v1/users",
        json={
            "member_id": str(target_member.id),
            "email": "new@example.com",
            "password": "CorrectHorse123!",
        },
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 201

    row = await _audit_row(db_session, "user.created")
    assert row is not None
    assert "hashed_password" not in (row.previous_value or {})
    assert "hashed_password" not in (row.new_value or {})


async def test_update_user_writes_audit_row(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    target_member = await make_member(role="partner")
    target_user = await make_user(target_member, "target@example.com")

    resp = await client.patch(
        f"/api/v1/users/{target_user.id}",
        json={"email": "renamed@example.com"},
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200

    row = await _audit_row(db_session, "user.updated")
    assert row is not None
    assert "hashed_password" not in (row.new_value or {})


async def test_deactivate_user_writes_audit_row(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    make_member: object,
    make_user: object,
) -> None:
    target_member = await make_member(role="partner")
    target_user = await make_user(target_member, "target@example.com")

    resp = await client.delete(
        f"/api/v1/users/{target_user.id}",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 204

    row = await _audit_row(db_session, "user.deactivated")
    assert row is not None
    assert "hashed_password" not in (row.new_value or {})


async def test_partner_cannot_create_user(
    client: AsyncClient,
    household: Household,
    make_member: object,
    make_user: object,
) -> None:
    partner_member = await make_member(role="partner")
    partner_user = await make_user(partner_member, "partner@example.com")

    resp = await client.post(
        "/api/v1/users",
        json={
            "member_id": str(partner_member.id),
            "email": "new@example.com",
            "password": "CorrectHorse123!",
        },
        headers=auth_headers(partner_user, partner_member, "partner"),
    )
    assert resp.status_code == 403
