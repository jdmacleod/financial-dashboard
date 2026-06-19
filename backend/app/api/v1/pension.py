import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.pension import PensionAccountCreate, PensionAccountResponse, PensionAccountUpdate
from app.services.pension import PensionService, _to_response

router = APIRouter()


@router.get("/accounts/{account_id}/pension", response_model=PensionAccountResponse)
async def get_pension(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PensionAccountResponse:
    svc = PensionService(session)
    return await svc.get(ctx, account_id)


@router.post(
    "/accounts/{account_id}/pension", response_model=PensionAccountResponse, status_code=201
)
async def create_pension(
    account_id: uuid.UUID,
    data: PensionAccountCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PensionAccountResponse:
    svc = PensionService(session)
    pension = await svc.create(ctx, account_id, data)
    await session.commit()
    await session.refresh(pension)
    return _to_response(pension)


@router.patch("/accounts/{account_id}/pension", response_model=PensionAccountResponse)
async def update_pension(
    account_id: uuid.UUID,
    data: PensionAccountUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PensionAccountResponse:
    svc = PensionService(session)
    pension = await svc.update(ctx, account_id, data)
    await session.commit()
    await session.refresh(pension)
    return _to_response(pension)
