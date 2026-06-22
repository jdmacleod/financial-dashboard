from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.insurance_policy import InsurancePolicyResponse
from app.services.insurance_policy import InsurancePolicyService

router = APIRouter()


@router.get("/insurance-policies", response_model=list[InsurancePolicyResponse])
async def list_insurance_policies(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[InsurancePolicyResponse]:
    svc = InsurancePolicyService(session)
    policies = await svc.list_policies(ctx)
    return [InsurancePolicyResponse.model_validate(p) for p in policies]
