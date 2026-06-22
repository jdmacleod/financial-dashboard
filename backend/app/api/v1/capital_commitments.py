from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.capital_commitment import CapitalCommitmentResponse
from app.services.private_fund import PrivateFundService

router = APIRouter()


@router.get("/capital-commitments", response_model=list[CapitalCommitmentResponse])
async def list_capital_commitments(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[CapitalCommitmentResponse]:
    svc = PrivateFundService(session)
    return await svc.list_commitments(ctx)
