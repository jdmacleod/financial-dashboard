import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.capital_commitment import (
    CapitalCommitmentCreate,
    CapitalCommitmentResponse,
    CapitalCommitmentUpdate,
)
from app.services.private_fund import PrivateFundService

router = APIRouter()


@router.get("/capital-commitments", response_model=list[CapitalCommitmentResponse])
async def list_capital_commitments(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[CapitalCommitmentResponse]:
    svc = PrivateFundService(session)
    return await svc.list_commitments(ctx)


@router.post(
    "/capital-commitments",
    response_model=CapitalCommitmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_capital_commitment(
    data: CapitalCommitmentCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CapitalCommitmentResponse:
    svc = PrivateFundService(session)
    commitment = await svc.create(ctx, data)
    return svc.to_response(commitment)


@router.patch("/capital-commitments/{commitment_id}", response_model=CapitalCommitmentResponse)
async def update_capital_commitment(
    commitment_id: uuid.UUID,
    data: CapitalCommitmentUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> CapitalCommitmentResponse:
    svc = PrivateFundService(session)
    commitment = await svc.update(ctx, commitment_id, data)
    return svc.to_response(commitment)


@router.delete("/capital-commitments/{commitment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capital_commitment(
    commitment_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = PrivateFundService(session)
    await svc.delete(ctx, commitment_id)
