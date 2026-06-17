import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.snapshot import SnapshotCreate, SnapshotResponse, SnapshotUpdate
from app.services.snapshot import SnapshotService

router = APIRouter()


@router.get("/accounts/{account_id}/snapshots", response_model=list[SnapshotResponse])
async def list_snapshots(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[SnapshotResponse]:
    svc = SnapshotService(session)
    snapshots = await svc.list_snapshots(ctx, account_id)
    return [SnapshotResponse.model_validate(s) for s in snapshots]


@router.post("/accounts/{account_id}/snapshots", response_model=SnapshotResponse, status_code=201)
async def create_snapshot(
    account_id: uuid.UUID,
    data: SnapshotCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> SnapshotResponse:
    svc = SnapshotService(session)
    snapshot = await svc.create(ctx, account_id, data)
    await session.commit()
    await session.refresh(snapshot)
    return SnapshotResponse.model_validate(snapshot)


@router.patch("/accounts/{account_id}/snapshots/{snapshot_id}", response_model=SnapshotResponse)
async def update_snapshot(
    account_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    data: SnapshotUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> SnapshotResponse:
    svc = SnapshotService(session)
    snapshot = await svc.update(ctx, account_id, snapshot_id, data)
    await session.commit()
    await session.refresh(snapshot)
    return SnapshotResponse.model_validate(snapshot)


@router.delete("/accounts/{account_id}/snapshots/{snapshot_id}", status_code=204)
async def delete_snapshot(
    account_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = SnapshotService(session)
    await svc.delete(ctx, account_id, snapshot_id)
    await session.commit()
