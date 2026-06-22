import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.advisory_note import (
    AdvisoryNoteCreate,
    AdvisoryNoteResponse,
    AdvisoryNoteUpdate,
)
from app.services.advisory_note import AdvisoryNoteService

router = APIRouter()


@router.get("/advisory-notes", response_model=list[AdvisoryNoteResponse])
async def list_advisory_notes(
    account_id: uuid.UUID | None = Query(default=None),
    ownership_entity_id: uuid.UUID | None = Query(default=None),
    category: str | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[AdvisoryNoteResponse]:
    svc = AdvisoryNoteService(session)
    notes = await svc.list_notes(
        ctx,
        account_id=account_id,
        ownership_entity_id=ownership_entity_id,
        category=category,
    )
    return [AdvisoryNoteResponse.model_validate(n) for n in notes]


@router.post(
    "/advisory-notes",
    response_model=AdvisoryNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_advisory_note(
    data: AdvisoryNoteCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> AdvisoryNoteResponse:
    svc = AdvisoryNoteService(session)
    note = await svc.create(ctx, data)
    return AdvisoryNoteResponse.model_validate(note)


@router.patch("/advisory-notes/{note_id}", response_model=AdvisoryNoteResponse)
async def update_advisory_note(
    note_id: uuid.UUID,
    data: AdvisoryNoteUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> AdvisoryNoteResponse:
    svc = AdvisoryNoteService(session)
    note = await svc.update(ctx, note_id, data)
    return AdvisoryNoteResponse.model_validate(note)


@router.delete("/advisory-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_advisory_note(
    note_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = AdvisoryNoteService(session)
    await svc.delete(ctx, note_id)
