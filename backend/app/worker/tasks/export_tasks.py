from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.db.models.audit_log import AuditLog
from app.db.models.export_job import ExportJob


async def run_export_job(ctx: dict[str, Any], job_id: str) -> None:
    """ARQ worker task: generate a PDF or Excel export file."""
    from app.exporters import excel_exporter, pdf_exporter

    session_factory = ctx["db"]
    async with session_factory() as session:
        result = await session.execute(select(ExportJob).where(ExportJob.id == uuid.UUID(job_id)))
        job = result.scalar_one()

        job.status = "processing"
        await session.commit()

        try:
            if job.export_type.startswith("pdf"):
                filename = await pdf_exporter.generate(job, session, settings.export_path)
            else:
                filename = await excel_exporter.generate(job, session, settings.export_path)

            now = datetime.now(UTC)
            job.status = "complete"
            job.filename = filename
            job.completed_at = now
            await session.flush()

            # Write audit log entry — no PII, no encrypted field values
            audit_entry = AuditLog(
                household_id=job.household_id,
                user_id=job.generated_by,
                action="export.generated",
                entity_type="export_job",
                entity_id=job.id,
                new_value={
                    "export_type": job.export_type,
                    "anonymized": job.anonymized,
                    "from_date": job.parameters.get("from_date"),
                    "to_date": job.parameters.get("to_date"),
                    "filename": filename,
                },
                ip_address=None,
                created_at=now,
            )
            session.add(audit_entry)
            await session.commit()

        except Exception as exc:
            await session.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            await session.commit()
