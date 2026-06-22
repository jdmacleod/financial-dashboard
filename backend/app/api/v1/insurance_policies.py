import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.insurance_policy import (
    InsurancePolicyCreate,
    InsurancePolicyResponse,
    InsurancePolicyUpdate,
)
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


@router.post(
    "/insurance-policies",
    response_model=InsurancePolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_insurance_policy(
    data: InsurancePolicyCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> InsurancePolicyResponse:
    svc = InsurancePolicyService(session)
    policy = await svc.create(ctx, data)
    return InsurancePolicyResponse.model_validate(policy)


@router.patch("/insurance-policies/{policy_id}", response_model=InsurancePolicyResponse)
async def update_insurance_policy(
    policy_id: uuid.UUID,
    data: InsurancePolicyUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> InsurancePolicyResponse:
    svc = InsurancePolicyService(session)
    policy = await svc.update(ctx, policy_id, data)
    return InsurancePolicyResponse.model_validate(policy)


@router.delete("/insurance-policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_insurance_policy(
    policy_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = InsurancePolicyService(session)
    await svc.delete(ctx, policy_id)
