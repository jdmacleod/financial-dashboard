import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.advisory_note import AdvisoryNoteResponse
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
