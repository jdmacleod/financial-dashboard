"""Tests for the export ARQ worker task (run_export_job).

The task function is invoked directly — no Redis container needed.
Exporter generate() calls are mocked to avoid file I/O.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit_log import AuditLog
from app.db.models.export_job import ExportJob
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.worker.tasks.export_tasks import run_export_job


def _now() -> datetime:
    return datetime.now(UTC)


async def _make_job(
    db_session: AsyncSession,
    household: Household,
    user: User,
    member: HouseholdMember,
    export_type: str = "pdf_summary",
) -> ExportJob:
    job = ExportJob(
        id=uuid.uuid4(),
        household_id=household.id,
        export_type=export_type,
        anonymized=not export_type.endswith("executor"),
        parameters={
            "from_date": "2024-01-01",
            "to_date": "2024-12-31",
            "member_id": str(member.id),
            "role": "primary",
        },
        status="pending",
        generated_by=user.id,
        created_at=_now(),
    )
    db_session.add(job)
    await db_session.flush()
    return job


def _make_ctx(db_session: AsyncSession) -> dict[str, Any]:
    """Build an ARQ ctx dict that wraps the existing test session."""

    @asynccontextmanager
    async def _session_cm() -> AsyncIterator[AsyncSession]:
        yield db_session

    return {"db": _session_cm}


async def test_run_export_job_pdf_sets_status_complete(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Successful PDF job transitions to complete and sets filename."""
    job = await _make_job(db_session, household, primary_user, primary_member, "pdf_summary")
    ctx = _make_ctx(db_session)

    expected_filename = "hearthledger_pdf_summary_2024-01-01T00-00-00Z.pdf"

    with patch("app.worker.tasks.export_tasks.pdf_exporter") as mock_pdf:
        mock_pdf.generate = AsyncMock(return_value=expected_filename)
        await run_export_job(ctx, str(job.id))

    await db_session.refresh(job)
    assert job.status == "complete"
    assert job.filename == expected_filename
    assert job.completed_at is not None


async def test_run_export_job_excel_calls_excel_exporter(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Excel job type routes to excel_exporter.generate()."""
    job = await _make_job(db_session, household, primary_user, primary_member, "excel_summary")
    ctx = _make_ctx(db_session)

    expected_filename = "hearthledger_excel_summary_2024-01-01T00-00-00Z.xlsx"

    with patch("app.worker.tasks.export_tasks.excel_exporter") as mock_excel:
        mock_excel.generate = AsyncMock(return_value=expected_filename)
        await run_export_job(ctx, str(job.id))

    await db_session.refresh(job)
    assert job.status == "complete"
    assert job.filename == expected_filename


async def test_run_export_job_writes_audit_log(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Successful export writes an audit log entry with no PII."""
    job = await _make_job(db_session, household, primary_user, primary_member, "pdf_summary")
    ctx = _make_ctx(db_session)

    with patch("app.worker.tasks.export_tasks.pdf_exporter") as mock_pdf:
        mock_pdf.generate = AsyncMock(return_value="test.pdf")
        await run_export_job(ctx, str(job.id))

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == job.id).order_by(AuditLog.created_at.desc())
    )
    audit = result.scalar_one_or_none()
    assert audit is not None
    assert audit.action == "export.generated"
    assert audit.entity_type == "export_job"
    assert audit.new_value["export_type"] == "pdf_summary"
    assert audit.new_value["filename"] == "test.pdf"
    # No encrypted field values
    assert "institution_name_enc" not in str(audit.new_value)
    assert "account_number_enc" not in str(audit.new_value)


async def test_run_export_job_failure_sets_status_failed(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """When the exporter raises, job transitions to failed with error_message."""
    job = await _make_job(db_session, household, primary_user, primary_member, "pdf_summary")
    ctx = _make_ctx(db_session)

    with patch("app.worker.tasks.export_tasks.pdf_exporter") as mock_pdf:
        mock_pdf.generate = AsyncMock(side_effect=RuntimeError("WeasyPrint font error"))
        await run_export_job(ctx, str(job.id))

    await db_session.refresh(job)
    assert job.status == "failed"
    assert "WeasyPrint font error" in job.error_message


async def test_run_export_job_excel_executor(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Executor Excel job also routes to excel_exporter.generate()."""
    job = await _make_job(db_session, household, primary_user, primary_member, "excel_executor")
    ctx = _make_ctx(db_session)

    with patch("app.worker.tasks.export_tasks.excel_exporter") as mock_excel:
        mock_excel.generate = AsyncMock(return_value="hearthledger_excel_executor_test.xlsx")
        await run_export_job(ctx, str(job.id))

    await db_session.refresh(job)
    assert job.status == "complete"
    assert job.anonymized is False
