from __future__ import annotations

import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.export_job import ExportCreate, ExportCreateResponse, ExportJobResponse
from app.services.export_service import ExportService
from app.worker.queue import get_arq_pool

router = APIRouter()


@router.post("/exports", response_model=ExportCreateResponse, status_code=201)
async def create_export(
    data: ExportCreate,
    x_reauth_token: str | None = Header(default=None, alias="X-Reauth-Token"),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> ExportCreateResponse:
    svc = ExportService(session, arq_pool)
    job = await svc.create(ctx, data, reauth_token=x_reauth_token)
    return ExportCreateResponse(export_job_id=job.id)


@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> list[ExportJobResponse]:
    svc = ExportService(session, arq_pool)
    jobs = await svc.list(ctx)
    return [ExportJobResponse.model_validate(j) for j in jobs]


@router.get("/exports/{job_id}", response_model=ExportJobResponse)
async def get_export(
    job_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> ExportJobResponse:
    svc = ExportService(session, arq_pool)
    job = await svc.get(ctx, job_id)
    return ExportJobResponse.model_validate(job)


@router.get("/exports/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> FileResponse:
    svc = ExportService(session, arq_pool)
    job = await svc.get(ctx, job_id)
    file_path = await svc.get_file_path(ctx, job_id)

    if job.export_type.startswith("pdf"):
        media_type = "application/pdf"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=job.filename,
    )
