import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, require_session_ctx
from app.db.base import get_session
from app.schemas.pat import PATCreatedResponse, PATCreateRequest, PATResponse
from app.services.pat import PATService

router = APIRouter()

# PAT management is intentionally session-only (require_session_ctx, not the
# JWT-or-PAT dependency): a PAT carries only the import-write capability and must
# never be usable to mint or revoke tokens — that would be privilege escalation.


@router.post(
    "/personal-access-tokens",
    response_model=PATCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pat(
    body: PATCreateRequest,
    ctx: VisibilityContext = Depends(require_session_ctx),
    session: AsyncSession = Depends(get_session),
) -> PATCreatedResponse:
    pat, token = await PATService(session).create(ctx, body.label, body.expires_in_days)
    return PATCreatedResponse(**PATResponse.model_validate(pat).model_dump(), token=token)


@router.get("/personal-access-tokens", response_model=list[PATResponse])
async def list_pats(
    ctx: VisibilityContext = Depends(require_session_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[PATResponse]:
    pats = await PATService(session).list(ctx)
    return [PATResponse.model_validate(p) for p in pats]


@router.delete("/personal-access-tokens/{pat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_pat(
    pat_id: uuid.UUID,
    ctx: VisibilityContext = Depends(require_session_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    await PATService(session).revoke(ctx, pat_id)
