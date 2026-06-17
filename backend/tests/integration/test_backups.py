"""Integration tests for backup API endpoints."""

from __future__ import annotations

from httpx import AsyncClient

from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_trigger_backup_creates_job(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post("/api/v1/backups", headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["triggered_by"] == "manual"
    assert data["triggered_by_user_id"] == str(primary_user.id)


async def test_trigger_backup_forbidden_for_partner(
    client: AsyncClient,
    household: Household,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    headers = auth_headers(partner_user, partner_member, "partner")
    resp = await client.post("/api/v1/backups", headers=headers)
    assert resp.status_code == 403


async def test_list_backups_returns_jobs(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    await client.post("/api/v1/backups", headers=headers)

    resp = await client.get("/api/v1/backups", headers=headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    assert jobs[0]["triggered_by"] == "manual"


async def test_list_backups_forbidden_for_partner(
    client: AsyncClient,
    household: Household,
    partner_member: HouseholdMember,
    partner_user: User,
) -> None:
    headers = auth_headers(partner_user, partner_member, "partner")
    resp = await client.get("/api/v1/backups", headers=headers)
    assert resp.status_code == 403


async def test_download_backup_not_ready_returns_404(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    create_resp = await client.post("/api/v1/backups", headers=headers)
    job_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/backups/{job_id}/download", headers=headers)
    assert resp.status_code == 404
