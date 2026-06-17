from __future__ import annotations

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.encryption import decrypt_file_to_devnull, encrypt_file
from app.db.models.backup_job import BackupJob

logger = logging.getLogger(__name__)


def _pg_url() -> str:
    """Convert asyncpg DSN to psycopg2-compatible URL for pg_dump."""
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def _prune_old_backups(backup_path: str, retention_days: int) -> None:
    cutoff = datetime.now(UTC).timestamp() - (retention_days * 86400)
    for f in Path(backup_path).glob("hearthledger_backup_*.dump.enc"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            logger.info("Pruned old backup: %s", f.name)


async def run_backup(ctx: dict[str, Any]) -> None:
    """ARQ worker task: pg_dump → AES-256-GCM encrypt → verify → prune."""
    started_at = datetime.now(UTC)
    ts = started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    filename = f"hearthledger_backup_{ts}.dump.enc"
    tmp_path = Path(f"/tmp/hearthledger_dump_{ts}.pgdump")  # noqa: S108
    out_dir = Path(settings.backup_path)
    out_path = out_dir / filename

    session_factory = ctx["db"]
    async with session_factory() as session:
        # Find the pending backup job if triggered manually, else create a new one
        job_id = ctx.get("backup_job_id")
        if job_id:
            result = await session.execute(select(BackupJob).where(BackupJob.id == job_id))
            job = result.scalar_one()
        else:
            job = BackupJob(
                triggered_by="scheduled",
                status="pending",
                started_at=started_at,
            )
            session.add(job)
            await session.flush()

        job.status = "processing"
        await session.commit()

        try:
            out_dir.mkdir(parents=True, exist_ok=True)

            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "pg_dump",
                    "--format=custom",
                    f"--file={tmp_path}",
                    _pg_url(),
                ],
                check=True,
                capture_output=True,
            )

            encrypt_file(tmp_path, out_path)
            decrypt_file_to_devnull(out_path)  # verify integrity
            _prune_old_backups(settings.backup_path, settings.backup_retention_days)

            file_size = out_path.stat().st_size
            now = datetime.now(UTC)
            job.status = "complete"
            job.filename = filename
            job.file_size_bytes = file_size
            job.completed_at = now
            await session.commit()
            logger.info("Backup complete: %s (%d bytes)", filename, file_size)

        except Exception as exc:
            await session.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            await session.commit()
            logger.exception("Backup failed: %s", exc)

        finally:
            tmp_path.unlink(missing_ok=True)
