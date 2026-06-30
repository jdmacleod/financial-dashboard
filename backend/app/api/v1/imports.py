import json
import uuid

from arq import ArqRedis
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import (
    VisibilityContext,
    get_visibility_ctx,
    require_import_write_ctx,
)
from app.db.base import get_session
from app.schemas.import_job import ImportJobResponse, ImportPreviewResponse
from app.schemas.staging import (
    ImportStagingRequest,
    ImportStagingResponse,
    StagingTransactionResponse,
)
from app.services.import_service import ImportService
from app.services.staging import StagingService
from app.worker.queue import get_arq_pool

router = APIRouter()


@router.post(
    "/accounts/{account_id}/import/staging",
    response_model=ImportStagingResponse,
    status_code=201,
)
async def stage_import(
    account_id: uuid.UUID,
    body: ImportStagingRequest,
    ctx: VisibilityContext = Depends(require_import_write_ctx),
    session: AsyncSession = Depends(get_session),
) -> ImportStagingResponse:
    """Accept pre-parsed rows from the ingest CLI into the staging table.

    Auth: a session writer OR a PAT carrying the import-write capability. Rows
    land unreviewed in ``staging_transactions`` and never affect balances until
    promoted. The server re-redacts PII and dedupes against committed + staged.
    """
    return await StagingService(session).stage(ctx, account_id, body)


@router.get(
    "/accounts/{account_id}/import/staging/{batch_id}",
    response_model=list[StagingTransactionResponse],
)
async def list_staging_batch(
    account_id: uuid.UUID,
    batch_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[StagingTransactionResponse]:
    rows = await StagingService(session).list_batch(ctx, account_id, batch_id)
    return [StagingTransactionResponse.model_validate(r) for r in rows]


@router.post("/accounts/{account_id}/import/preview", response_model=ImportPreviewResponse)
async def preview_import(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> ImportPreviewResponse:
    svc = ImportService(session, arq_pool)
    content = await file.read()
    return await svc.preview(ctx, account_id, content)


@router.post("/accounts/{account_id}/import", response_model=ImportJobResponse, status_code=201)
async def start_import(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    mapping: str | None = Form(None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> ImportJobResponse:
    svc = ImportService(session, arq_pool)
    content = await file.read()
    parsed_mapping = json.loads(mapping) if mapping else None
    job = await svc.start_import(
        ctx, account_id, file.filename or "upload", content, parsed_mapping
    )
    return ImportJobResponse.model_validate(job)


@router.get("/import-jobs/{job_id}", response_model=ImportJobResponse)
async def get_import_job(
    job_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> ImportJobResponse:
    svc = ImportService(session, arq_pool)
    job = await svc.get_job(ctx, job_id)
    return ImportJobResponse.model_validate(job)


@router.get("/import-jobs", response_model=list[ImportJobResponse])
async def list_import_jobs(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
    arq_pool: ArqRedis = Depends(get_arq_pool),
) -> list[ImportJobResponse]:
    svc = ImportService(session, arq_pool)
    jobs = await svc.list_jobs(ctx)
    return [ImportJobResponse.model_validate(j) for j in jobs]
