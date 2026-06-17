import uuid
from datetime import UTC, datetime

from arq import ArqRedis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.import_job import ImportJob
from app.importers.csv_importer import preview as csv_preview
from app.repositories.account import AccountRepository
from app.schemas.import_job import ImportPreviewResponse

SUPPORTED_EXTENSIONS = {"csv": "csv", "ofx": "ofx", "qfx": "qfx"}


def format_from_filename(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    fmt = SUPPORTED_EXTENSIONS.get(ext)
    if fmt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type; expected .csv, .ofx, or .qfx",
        )
    return fmt


class ImportService:
    def __init__(self, session: AsyncSession, arq_pool: ArqRedis) -> None:
        self.session = session
        self.arq_pool = arq_pool
        self.account_repo = AccountRepository(session)

    async def preview(
        self, ctx: VisibilityContext, account_id: uuid.UUID, content: bytes
    ) -> ImportPreviewResponse:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if not ctx.is_primary and account.owner_member_id not in (None, ctx.member_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        headers, preview_rows, suggested_mapping = csv_preview(content)
        return ImportPreviewResponse(
            headers=headers, preview_rows=preview_rows, suggested_mapping=suggested_mapping
        )

    async def start_import(
        self,
        ctx: VisibilityContext,
        account_id: uuid.UUID,
        filename: str,
        content: bytes,
        mapping: dict[str, str] | None,
    ) -> ImportJob:
        account = await self.account_repo.get_by_id(ctx, account_id)
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if not ctx.is_primary and account.owner_member_id not in (None, ctx.member_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        fmt = format_from_filename(filename)
        now = datetime.now(UTC)
        job = ImportJob(
            account_id=account_id,
            filename=filename,
            format=fmt,
            status="pending",
            imported_by=ctx.user_id,
            created_at=now,
            updated_at=now,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        await self.session.commit()

        await self.arq_pool.enqueue_job(
            "run_import_job", str(job.id), content, fmt, mapping, str(ctx.household_id)
        )
        return job

    async def get_job(self, ctx: VisibilityContext, job_id: uuid.UUID) -> ImportJob:
        result = await self.session.execute(select(ImportJob).where(ImportJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found"
            )
        await self.account_repo.get_by_id(ctx, job.account_id)
        return job

    async def list_jobs(self, ctx: VisibilityContext) -> list[ImportJob]:
        visible_accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in visible_accounts]
        if not account_ids:
            return []
        result = await self.session.execute(
            select(ImportJob)
            .where(ImportJob.account_id.in_(account_ids))
            .order_by(ImportJob.created_at.desc())
            .limit(20)
        )
        return list(result.scalars().all())
