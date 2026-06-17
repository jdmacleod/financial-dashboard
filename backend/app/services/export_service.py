from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from arq import ArqRedis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.core.visibility import VisibilityContext
from app.db.models.export_job import ExportJob
from app.schemas.export_job import ExportCreate


class ExportService:
    def __init__(self, session: AsyncSession, arq_pool: ArqRedis) -> None:
        self.session = session
        self.arq_pool = arq_pool

    async def create(
        self,
        ctx: VisibilityContext,
        data: ExportCreate,
        reauth_token: str | None = None,
    ) -> ExportJob:
        """Creates an export job and enqueues it.

        Executor exports (pdf_executor, excel_executor) require:
          - primary role
          - a valid, single-use reauth token passed in X-Reauth-Token header
        """
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        is_executor = data.export_type in ("pdf_executor", "excel_executor")
        anonymized = not is_executor

        if is_executor:
            if not ctx.is_primary:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Executor exports require the primary role",
                )
            if not reauth_token:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Executor export requires re-authentication",
                )
            # Validate the reauth JWT
            try:
                decode_token(reauth_token, "reauth")
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid or expired reauth token",
                ) from exc

            # Single-use enforcement via Redis
            token_hash = hashlib.sha256(reauth_token.encode()).hexdigest()
            already_used = await self.arq_pool.get(f"reauth_used:{token_hash}")
            if already_used:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Executor export requires re-authentication",
                )
            await self.arq_pool.set(f"reauth_used:{token_hash}", "1", ex=600)

        include_transactions = (
            data.include_transactions if data.include_transactions is not None else True
        )

        params = {
            "from_date": str(data.from_date),
            "to_date": str(data.to_date),
            "account_ids": [str(a) for a in data.account_ids] if data.account_ids else None,
            "include_transactions": include_transactions,
            "member_id": str(ctx.member_id) if ctx.member_id else None,
            "role": ctx.role,
        }

        now = datetime.now(UTC)
        job = ExportJob(
            household_id=ctx.household_id,
            export_type=data.export_type,
            anonymized=anonymized,
            parameters=params,
            status="pending",
            generated_by=ctx.user_id,
            created_at=now,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        await self.session.commit()

        await self.arq_pool.enqueue_job("run_export_job", str(job.id))
        return job

    async def get(self, ctx: VisibilityContext, job_id: uuid.UUID) -> ExportJob:
        result = await self.session.execute(select(ExportJob).where(ExportJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None or job.household_id != ctx.household_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found",
            )
        return job

    async def list(self, ctx: VisibilityContext) -> list[ExportJob]:
        result = await self.session.execute(
            select(ExportJob)
            .where(ExportJob.household_id == ctx.household_id)
            .order_by(ExportJob.created_at.desc())
            .limit(30)
        )
        return list(result.scalars().all())

    async def get_file_path(self, ctx: VisibilityContext, job_id: uuid.UUID) -> str:
        from app.core.config import settings

        job = await self.get(ctx, job_id)
        if job.status != "complete" or not job.filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not ready",
            )
        import os

        return os.path.join(settings.export_path, job.filename)
