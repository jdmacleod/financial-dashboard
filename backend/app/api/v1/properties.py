import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.real_estate import (
    PropertyCreate,
    PropertyEquityResponse,
    PropertyResponse,
    PropertyUpdate,
    ValuationCreate,
    ValuationResponse,
)
from app.services.real_estate import RealEstateService

router = APIRouter()


@router.get("/accounts/{account_id}/property", response_model=PropertyResponse)
async def get_property_by_account(
    account_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyResponse:
    svc = RealEstateService(session)
    return await svc.get_by_account(ctx, account_id)


@router.post("/properties", response_model=PropertyResponse, status_code=201)
async def create_property(
    data: PropertyCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyResponse:
    svc = RealEstateService(session)
    property_ = await svc.create(ctx, data)
    await session.commit()
    return property_


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyResponse:
    svc = RealEstateService(session)
    return await svc.get(ctx, property_id)


@router.patch("/properties/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: uuid.UUID,
    data: PropertyUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyResponse:
    svc = RealEstateService(session)
    property_ = await svc.update(ctx, property_id, data)
    await session.commit()
    return property_


@router.get("/properties/{property_id}/equity", response_model=PropertyEquityResponse)
async def get_property_equity(
    property_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> PropertyEquityResponse:
    svc = RealEstateService(session)
    return await svc.get_equity(ctx, property_id)


@router.get("/properties/{property_id}/valuations", response_model=list[ValuationResponse])
async def list_valuations(
    property_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[ValuationResponse]:
    svc = RealEstateService(session)
    valuations = await svc.list_valuations(ctx, property_id)
    return [ValuationResponse.model_validate(v) for v in valuations]


@router.post(
    "/properties/{property_id}/valuations", response_model=ValuationResponse, status_code=201
)
async def add_valuation(
    property_id: uuid.UUID,
    data: ValuationCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> ValuationResponse:
    svc = RealEstateService(session)
    valuation = await svc.add_valuation(ctx, property_id, data)
    await session.commit()
    await session.refresh(valuation)
    return ValuationResponse.model_validate(valuation)
