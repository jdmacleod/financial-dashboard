from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.schemas.fire import (
    FireDetectionResponse,
    FireProjectionResponse,
    FireScenarioCreate,
    FireScenarioResponse,
    FireScenarioUpdate,
)
from app.services.fire_service import FireScenarioService

router = APIRouter()


@router.get("/fire-scenarios", response_model=list[FireScenarioResponse])
async def list_fire_scenarios(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> list[FireScenarioResponse]:
    svc = FireScenarioService(session)
    return await svc.list(ctx)


@router.post("/fire-scenarios", response_model=FireScenarioResponse, status_code=201)
async def create_fire_scenario(
    data: FireScenarioCreate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FireScenarioResponse:
    svc = FireScenarioService(session)
    scenario = await svc.create(ctx, data)
    await session.commit()
    return scenario


@router.get("/fire-scenarios/{scenario_id}", response_model=FireScenarioResponse)
async def get_fire_scenario(
    scenario_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FireScenarioResponse:
    svc = FireScenarioService(session)
    return await svc.get(ctx, scenario_id)


@router.patch("/fire-scenarios/{scenario_id}", response_model=FireScenarioResponse)
async def update_fire_scenario(
    scenario_id: uuid.UUID,
    data: FireScenarioUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FireScenarioResponse:
    svc = FireScenarioService(session)
    scenario = await svc.update(ctx, scenario_id, data)
    await session.commit()
    return scenario


@router.delete("/fire-scenarios/{scenario_id}", status_code=204)
async def delete_fire_scenario(
    scenario_id: uuid.UUID,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> None:
    svc = FireScenarioService(session)
    await svc.delete(ctx, scenario_id)
    await session.commit()


@router.post("/fire-scenarios/{scenario_id}/detect", response_model=FireDetectionResponse)
async def detect_fire_inputs(
    scenario_id: uuid.UUID,
    trailing_months: int = Query(default=12, ge=1, le=60),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FireDetectionResponse:
    svc = FireScenarioService(session)
    result = await svc.detect(ctx, scenario_id, trailing_months=trailing_months)
    await session.commit()
    return result


@router.get("/fire-scenarios/{scenario_id}/projection", response_model=FireProjectionResponse)
async def get_fire_projection(
    scenario_id: uuid.UUID,
    from_year: int | None = Query(default=None),
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> FireProjectionResponse:
    svc = FireScenarioService(session)
    return await svc.project(ctx, scenario_id, from_year=from_year)
