from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.backup_job import BackupJob


class BackupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, ctx: VisibilityContext) -> BackupJob:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        job = BackupJob(
            triggered_by="manual",
            triggered_by_user_id=ctx.user_id,
            status="pending",
            started_at=datetime.now(UTC),
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        await self.session.commit()
        return job

    async def list(self, ctx: VisibilityContext) -> list[BackupJob]:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        result = await self.session.execute(
            select(BackupJob).order_by(BackupJob.started_at.desc()).limit(50)
        )
        return list(result.scalars().all())

    async def get(self, ctx: VisibilityContext, job_id: uuid.UUID) -> BackupJob:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        result = await self.session.execute(select(BackupJob).where(BackupJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found")
        return job
