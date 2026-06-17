"""Integration tests for the exports API endpoints."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_reauth_token
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User

from ..conftest import auth_headers


async def test_create_summary_export_returns_job_id(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        "/api/v1/exports",
        json={"export_type": "pdf_summary", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "export_job_id" in data
    assert data["export_job_id"]


async def test_list_exports_returns_jobs(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    # Create a job first
    await client.post(
        "/api/v1/exports",
        json={"export_type": "excel_summary", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        headers=headers,
    )
    resp = await client.get("/api/v1/exports", headers=headers)
    assert resp.status_code == 200
    jobs = resp.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    assert jobs[0]["export_type"] == "excel_summary"


async def test_get_export_by_id(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    create_resp = await client.post(
        "/api/v1/exports",
        json={"export_type": "pdf_summary", "from_date": "2025-01-01", "to_date": "2025-06-30"},
        headers=headers,
    )
    job_id = create_resp.json()["export_job_id"]

    get_resp = await client.get(f"/api/v1/exports/{job_id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == job_id
    assert data["export_type"] == "pdf_summary"
    assert data["status"] == "pending"
    assert data["anonymized"] is True


async def test_get_export_unknown_id_returns_404(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    import uuid

    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.get(f"/api/v1/exports/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


async def test_create_executor_export_no_reauth_returns_403(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.post(
        "/api/v1/exports",
        json={"export_type": "pdf_executor", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_create_executor_export_with_reauth_succeeds(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    reauth = create_reauth_token(str(primary_user.id))
    headers = {
        **auth_headers(primary_user, primary_member, "primary"),
        "X-Reauth-Token": reauth,
    }
    resp = await client.post(
        "/api/v1/exports",
        json={
            "export_type": "excel_executor",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "export_job_id" in data


async def test_partner_cannot_create_executor_export(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    make_member: object,
    make_user: object,
    primary_user: User,
) -> None:
    from collections.abc import Callable
    from typing import Any

    _make_member: Callable[..., Any] = make_member  # type: ignore[assignment]
    _make_user: Callable[..., Any] = make_user  # type: ignore[assignment]
    partner = await _make_member(role="partner", display_name="Partner")
    partner_user = await _make_user(partner, "partner2@example.com")

    reauth = create_reauth_token(str(partner_user.id))
    headers = {
        **auth_headers(partner_user, partner, "partner"),
        "X-Reauth-Token": reauth,
    }
    resp = await client.post(
        "/api/v1/exports",
        json={"export_type": "pdf_executor", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_download_pending_job_returns_404(
    client: AsyncClient,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    create_resp = await client.post(
        "/api/v1/exports",
        json={"export_type": "pdf_summary", "from_date": "2025-01-01", "to_date": "2025-12-31"},
        headers=headers,
    )
    job_id = create_resp.json()["export_job_id"]
    dl_resp = await client.get(f"/api/v1/exports/{job_id}/download", headers=headers)
    assert dl_resp.status_code == 404
