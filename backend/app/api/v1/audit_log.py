import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.audit import PaginatedAuditLog
from app.services.audit import AuditLogService

router = APIRouter()


@router.get("/audit-log", response_model=PaginatedAuditLog)
async def list_audit_log(
    entity_type: str | None = Query(None),
    entity_id: uuid.UUID | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    member_id: uuid.UUID | None = Query(None),
    from_: datetime | None = Query(None, alias="from"),
    to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PaginatedAuditLog:
    svc = AuditLogService(session)
    return await svc.list_entries(
        ctx,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        member_id=member_id,
        from_date=from_,
        to_date=to,
        page=page,
        page_size=page_size,
    )
