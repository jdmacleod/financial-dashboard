"""Phase 6 acceptance criteria — Polish (Backup, Valuation, Dashboard, Import History)."""

from __future__ import annotations

import tempfile
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.backup_job import BackupJob
from app.db.models.household import Household
from app.db.models.import_job import ImportJob
from app.db.models.member import HouseholdMember
from app.db.models.property_valuation import PropertyValuation
from app.db.models.real_estate import RealEstateProperty
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


@asynccontextmanager
async def _session_ctx(session: AsyncSession):  # type: ignore[type-arg]
    yield session


def _arq_ctx(session: AsyncSession, **kwargs: Any) -> dict[str, Any]:
    ctx: dict[str, Any] = {"db": lambda: _session_ctx(session)}
    ctx.update(kwargs)
    return ctx


# ── AC 1 / AC 2: backup task + AES-256-GCM round-trip ────────────────────────


async def test_trigger_backup_produces_encrypted_file(db_session: AsyncSession) -> None:
    """AC1/AC2: run_backup produces an AES-256-GCM file that decrypts correctly.

    pg_dump is patched; encrypt_file and decrypt_file_to_devnull run for real so
    the full encrypt→verify round-trip (AC2) is exercised.
    """
    import pathlib

    from app.db.models.backup_job import BackupJob
    from app.worker.tasks.backup_tasks import run_backup

    job = BackupJob(triggered_by="manual", status="pending")
    db_session.add(job)
    await db_session.flush()

    fake_dump_content = b"PGDMP" + b"\x00" * 100

    def fake_pg_dump(cmd: list[str], **kwargs: Any) -> MagicMock:
        # The task passes --file=<path>; extract the path and write fake bytes.
        for part in cmd:
            if part.startswith("--file="):
                pathlib.Path(part[len("--file=") :]).write_bytes(fake_dump_content)
                break
        return MagicMock(returncode=0)

    with tempfile.TemporaryDirectory() as tmp_dir:
        with (
            patch(
                "app.worker.tasks.backup_tasks.subprocess.run",
                side_effect=fake_pg_dump,
            ),
            patch("app.worker.tasks.backup_tasks.settings") as mock_cfg,
            patch("app.worker.tasks.backup_tasks._prune_old_backups"),
        ):
            mock_cfg.database_url = "postgresql+asyncpg://x:y@localhost/db"
            mock_cfg.backup_path = tmp_dir
            mock_cfg.backup_retention_days = 30

            await run_backup(_arq_ctx(db_session, backup_job_id=str(job.id)))

        await db_session.refresh(job)
        assert job.status == "complete", f"Expected complete, got {job.status}: {job.error_message}"
        assert job.filename is not None
        assert job.filename.endswith(".dump.enc")

        # AC2: decrypt must succeed (verifies AES-GCM authentication tag)
        from app.core.encryption import decrypt_file_to_devnull

        out_path = pathlib.Path(tmp_dir) / job.filename
        assert out_path.exists(), "Encrypted file was not written to backup_path"
        decrypt_file_to_devnull(out_path)


# ── AC 3: Old backups are pruned ──────────────────────────────────────────────


async def test_old_backups_are_pruned_after_run() -> None:
    """AC3: _prune_old_backups removes files older than retention_days."""
    from app.worker.tasks.backup_tasks import _prune_old_backups

    with tempfile.TemporaryDirectory() as tmp_dir:
        import pathlib
        import time

        backup_dir = pathlib.Path(tmp_dir)

        # Create one old file (31 days ago) and one recent file (1 day ago)
        old_file = backup_dir / "hearthledger_backup_2024-01-01T00-00-00Z.dump.enc"
        new_file = backup_dir / "hearthledger_backup_2024-02-01T00-00-00Z.dump.enc"
        old_file.write_bytes(b"old")
        new_file.write_bytes(b"new")

        # Back-date the old file by 31 days
        old_mtime = time.time() - (31 * 86400)
        import os

        os.utime(old_file, (old_mtime, old_mtime))

        _prune_old_backups(tmp_dir, retention_days=30)

        assert not old_file.exists(), "Old backup should have been pruned"
        assert new_file.exists(), "Recent backup should NOT have been pruned"


# ── AC 4: Download endpoint streams correct content-type ─────────────────────


async def test_download_backup_streams_octet_stream(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
    primary_member: HouseholdMember,
    client: AsyncClient,
) -> None:
    """AC4: download endpoint returns Content-Type application/octet-stream."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        import pathlib

        filename = "hearthledger_backup_2024-01-15T02-00-00Z.dump.enc"
        fake_file = pathlib.Path(tmp_dir) / filename
        fake_file.write_bytes(b"encrypted_content")

        job = BackupJob(
            triggered_by="manual",
            status="complete",
            filename=filename,
            file_size_bytes=len(b"encrypted_content"),
            started_at=_now(),
            completed_at=_now(),
        )
        db_session.add(job)
        await db_session.commit()

        from app.core.config import settings as app_settings

        with patch.object(app_settings, "backup_path", tmp_dir):
            resp = await client.get(
                f"/api/v1/backups/{job.id}/download",
                headers=auth_headers(primary_user, primary_member, "primary"),
            )

        assert resp.status_code == 200, resp.text
        assert "octet-stream" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")


# ── AC 6: Valuation refresh creates new rows without overwriting manual ones ──


async def test_valuation_refresh_creates_api_rows_without_touching_manual(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
) -> None:
    """AC6/AC7: refresh_valuations creates new API valuation rows.
    Manual valuations are unmodified; API failures don't raise to caller.
    """
    from app.core.encryption import encrypt
    from app.db.models.account import Account
    from app.worker.tasks.valuation_tasks import refresh_valuations

    # Seed an account + property
    acct = Account(
        household_id=household.id,
        account_type="real_estate",
        nickname="My House",
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(acct)
    await db_session.flush()

    prop = RealEstateProperty(
        account_id=acct.id,
        address_enc=encrypt("123 Main St"),
        purchase_price=Decimal("400000"),
        purchase_date=date(2020, 1, 1),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(prop)
    await db_session.flush()

    manual_val = PropertyValuation(
        real_estate_property_id=prop.id,
        valuation_date=date(2024, 1, 1),
        estimated_value=Decimal("450000"),
        source="manual",
        created_at=_now(),
    )
    db_session.add(manual_val)
    await db_session.commit()

    # Mock ATTOM API to return a value
    async def fake_attom(address: str) -> tuple[Decimal, Decimal | None]:
        return Decimal("460000"), Decimal("0.87")

    with (
        patch("app.worker.tasks.valuation_tasks.settings") as mock_cfg,
        patch(
            "app.worker.tasks.valuation_tasks._get_estimate_attom",
            side_effect=fake_attom,
        ),
    ):
        mock_cfg.re_valuation_provider = "attom"
        await refresh_valuations(_arq_ctx(db_session))

    # Manual valuation is still there
    from sqlalchemy import select

    result = await db_session.execute(
        select(PropertyValuation).where(PropertyValuation.real_estate_property_id == prop.id)
    )
    vals = result.scalars().all()
    assert len(vals) == 2
    sources = {v.source for v in vals}
    assert "manual" in sources
    assert "api_attom" in sources

    api_val = next(v for v in vals if v.source == "api_attom")
    assert api_val.estimated_value == Decimal("460000")
    assert api_val.confidence_score == Decimal("0.87")


# ── AC 7: Valuation API failure is swallowed; no exception raised ─────────────


async def test_valuation_refresh_swallows_provider_failure(
    db_session: AsyncSession,
    household: Household,
) -> None:
    """AC7: when the provider API call fails, the task completes without raising."""
    from app.core.encryption import encrypt
    from app.db.models.account import Account
    from app.worker.tasks.valuation_tasks import refresh_valuations

    acct = Account(
        household_id=household.id,
        account_type="real_estate",
        nickname="Failing Home",
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(acct)
    await db_session.flush()

    prop = RealEstateProperty(
        account_id=acct.id,
        address_enc=encrypt("456 Error Ave"),
        purchase_price=Decimal("300000"),
        purchase_date=date(2021, 6, 1),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(prop)
    await db_session.commit()

    async def exploding_api(address: str) -> tuple[Decimal, Decimal | None]:
        raise RuntimeError("ATTOM API unavailable")

    with (
        patch("app.worker.tasks.valuation_tasks.settings") as mock_cfg,
        patch(
            "app.worker.tasks.valuation_tasks._get_estimate_attom",
            side_effect=exploding_api,
        ),
    ):
        mock_cfg.re_valuation_provider = "attom"
        # Should NOT raise — failure is logged and swallowed
        await refresh_valuations(_arq_ctx(db_session))

    # No new valuations should have been created
    from sqlalchemy import select

    result = await db_session.execute(
        select(PropertyValuation).where(PropertyValuation.real_estate_property_id == prop.id)
    )
    vals = result.scalars().all()
    assert len(vals) == 0


# ── AC 8: Dashboard widget order persists per member ─────────────────────────


async def test_dashboard_layout_persists_independently_per_member(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
    primary_member: HouseholdMember,
    partner_user: User,
    partner_member: HouseholdMember,
    client: AsyncClient,
) -> None:
    """AC8: widget layout is per-member; primary and partner have independent settings."""
    primary_headers = auth_headers(primary_user, primary_member, "primary")
    partner_headers = auth_headers(partner_user, partner_member, "partner")

    primary_layout = [
        {"id": "net_worth", "visible": True, "order": 0},
        {"id": "cash_flow", "visible": False, "order": 1},
    ]
    partner_layout = [
        {"id": "cash_flow", "visible": True, "order": 0},
        {"id": "net_worth", "visible": True, "order": 1},
    ]

    # Primary saves their layout
    resp = await client.patch(
        f"/api/v1/members/{primary_member.id}/dashboard-layout",
        json={"widgets": primary_layout},
        headers=primary_headers,
    )
    assert resp.status_code == 200, resp.text

    # Partner saves their own layout
    resp = await client.patch(
        f"/api/v1/members/{partner_member.id}/dashboard-layout",
        json={"widgets": partner_layout},
        headers=partner_headers,
    )
    assert resp.status_code == 200, resp.text

    # Reload primary's layout and confirm it's unaffected by partner's save
    resp = await client.get(
        f"/api/v1/members/{primary_member.id}",
        headers=primary_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    widgets = body.get("settings", {}).get("dashboard_widgets", [])
    cash_flow_widget = next((w for w in widgets if w["id"] == "cash_flow"), None)
    assert cash_flow_widget is not None
    assert cash_flow_widget["visible"] is False  # primary hid it; partner showed it


# ── AC 10: Import history page uses existing GET /import-jobs endpoint ────────


async def test_import_history_lists_jobs_with_status_and_counts(
    db_session: AsyncSession,
    household: Household,
    primary_user: User,
    primary_member: HouseholdMember,
    client: AsyncClient,
) -> None:
    """AC10: GET /import-jobs returns jobs with status, records_imported, records_skipped."""
    from app.db.models.account import Account

    account = Account(
        household_id=household.id,
        account_type="checking",
        nickname="Test Account",
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()

    job_complete = ImportJob(
        account_id=account.id,
        filename="january.csv",
        format="csv",
        status="complete",
        records_found=50,
        records_imported=48,
        records_skipped=2,
        imported_by=primary_user.id,
        created_at=_now(),
        updated_at=_now(),
    )
    job_failed = ImportJob(
        account_id=account.id,
        filename="bad.ofx",
        format="ofx",
        status="failed",
        records_found=None,
        records_imported=None,
        records_skipped=None,
        error_message="Malformed OFX file",
        imported_by=primary_user.id,
        created_at=_now() - timedelta(days=1),
        updated_at=_now() - timedelta(days=1),
    )
    db_session.add(job_complete)
    db_session.add(job_failed)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/import-jobs",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    jobs = resp.json()
    assert isinstance(jobs, list)

    statuses = {j["status"] for j in jobs}
    assert "complete" in statuses
    assert "failed" in statuses

    complete_job = next(j for j in jobs if j["filename"] == "january.csv")
    assert complete_job["records_imported"] == 48
    assert complete_job["records_skipped"] == 2
    assert complete_job["format"] == "csv"
