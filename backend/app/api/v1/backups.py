from __future__ import annotations

import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.backup import BackupJobResponse
from app.services.backup import BackupService
from app.worker.queue import get_arq_pool

router = APIRouter()


@router.get("/backups", response_model=list[BackupJobResponse])
async def list_backups(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[BackupJobResponse]:
    svc = BackupService(session)
    jobs = await svc.list(ctx)
    return [BackupJobResponse.model_validate(j) for j in jobs]


@router.post("/backups", response_model=BackupJobResponse, status_code=201)
async def trigger_backup(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> BackupJobResponse:
    svc = BackupService(session)
    job = await svc.create(ctx)
    await arq_pool.enqueue_job("run_backup", _kwargs={"backup_job_id": str(job.id)})
    return BackupJobResponse.model_validate(job)


@router.get("/backups/{job_id}/download")
async def download_backup(
    job_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    svc = BackupService(session)
    job = await svc.get(ctx, job_id)
    if job.status != "complete" or not job.filename:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not ready",
        )
    import os

    file_path = os.path.join(settings.backup_path, job.filename)
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=job.filename,
    )
