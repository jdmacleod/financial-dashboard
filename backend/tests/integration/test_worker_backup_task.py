"""Integration tests for the run_backup ARQ task."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def _session_ctx(session: AsyncSession):  # type: ignore[type-arg]
    yield session


def _arq_ctx(session: AsyncSession, backup_job_id: str | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {"db": lambda: _session_ctx(session)}
    if backup_job_id is not None:
        d["backup_job_id"] = backup_job_id
    return d


async def test_run_backup_completes_successfully(db_session: AsyncSession) -> None:
    from app.db.models.backup_job import BackupJob
    from app.worker.tasks.backup_tasks import run_backup

    job = BackupJob(
        triggered_by="manual",
        triggered_by_user_id=uuid.uuid4(),
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()
    job_id = str(job.id)

    with (
        patch("app.worker.tasks.backup_tasks.subprocess.run") as mock_run,
        patch("app.worker.tasks.backup_tasks.encrypt_file") as mock_enc,
        patch("app.worker.tasks.backup_tasks.decrypt_file_to_devnull") as mock_dec,
        patch("app.worker.tasks.backup_tasks._prune_old_backups"),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        mock_stat.return_value = MagicMock(st_size=1024)
        await run_backup(_arq_ctx(db_session, backup_job_id=job_id))

    mock_run.assert_called_once()
    mock_enc.assert_called_once()
    mock_dec.assert_called_once()

    await db_session.refresh(job)
    assert job.status == "complete"
    assert job.filename is not None
    assert job.completed_at is not None


async def test_run_backup_sets_failed_on_error(db_session: AsyncSession) -> None:
    from app.db.models.backup_job import BackupJob
    from app.worker.tasks.backup_tasks import run_backup

    job = BackupJob(
        triggered_by="manual",
        triggered_by_user_id=uuid.uuid4(),
        status="pending",
    )
    db_session.add(job)
    await db_session.flush()
    job_id = str(job.id)

    with patch(
        "app.worker.tasks.backup_tasks.subprocess.run",
        side_effect=RuntimeError("pg_dump failed"),
    ):
        await run_backup(_arq_ctx(db_session, backup_job_id=job_id))

    await db_session.refresh(job)
    assert job.status == "failed"
    assert "pg_dump failed" in (job.error_message or "")


async def test_run_backup_creates_scheduled_job_when_no_id(db_session: AsyncSession) -> None:
    from app.worker.tasks.backup_tasks import run_backup

    with (
        patch("app.worker.tasks.backup_tasks.subprocess.run") as mock_run,
        patch("app.worker.tasks.backup_tasks.encrypt_file"),
        patch("app.worker.tasks.backup_tasks.decrypt_file_to_devnull"),
        patch("app.worker.tasks.backup_tasks._prune_old_backups"),
        patch("pathlib.Path.stat") as mock_stat,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        mock_stat.return_value = MagicMock(st_size=512)
        await run_backup(_arq_ctx(db_session))

    mock_run.assert_called_once()
