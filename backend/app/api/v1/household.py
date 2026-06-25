from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.visibility import VisibilityContext, get_visibility_ctx
from app.db.base import get_session
from app.db.models.household import Household
from app.schemas.household import (
    HouseholdResponse,
    HouseholdUpdate,
    ValuationConfigResponse,
    ValuationConfigUpdate,
)

router = APIRouter()


@router.get("/household", response_model=HouseholdResponse)
async def get_household(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> Household:
    result = await session.execute(select(Household).where(Household.id == ctx.household_id))
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=404)
    return household


@router.patch("/household", response_model=HouseholdResponse)
async def update_household(
    data: HouseholdUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
    session: AsyncSession = Depends(get_session),
) -> Household:
    if not ctx.is_primary:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    result = await session.execute(select(Household).where(Household.id == ctx.household_id))
    household = result.scalar_one_or_none()
    if not household:
        raise HTTPException(status_code=404)
    if data.name is not None:
        household.name = data.name
    if data.settings is not None:
        household.settings = data.settings
    # filing_status and state are nullable identity fields; use model_fields_set so
    # an explicit null in the payload clears them rather than being ignored.
    if "filing_status" in data.model_fields_set:
        household.filing_status = data.filing_status
    if "state" in data.model_fields_set:
        household.state = data.state
    await session.commit()
    await session.refresh(household)
    return household


@router.get("/settings/valuation-provider", response_model=ValuationConfigResponse)
async def get_valuation_config(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
) -> ValuationConfigResponse:
    if not ctx.is_primary:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return ValuationConfigResponse(
        provider=settings.re_valuation_provider,
        has_api_key=bool(settings.re_valuation_api_key),
    )


@router.patch("/settings/valuation-provider", response_model=ValuationConfigResponse)
async def update_valuation_config(
    data: ValuationConfigUpdate,
    ctx: VisibilityContext = Depends(get_visibility_ctx),
) -> ValuationConfigResponse:
    if not ctx.is_primary:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    valid_providers = {"manual", "attom", "estated"}
    if data.provider not in valid_providers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider must be one of: {', '.join(sorted(valid_providers))}",
        )

    # Write to .env file so the change survives restarts
    import os
    import re

    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path) as _f:
            env_text = _f.read()
        env_text = re.sub(
            r"^RE_VALUATION_PROVIDER=.*$",
            f"RE_VALUATION_PROVIDER={data.provider}",
            env_text,
            flags=re.MULTILINE,
        )
        if data.api_key is not None:
            env_text = re.sub(
                r"^RE_VALUATION_API_KEY=.*$",
                f"RE_VALUATION_API_KEY={data.api_key}",
                env_text,
                flags=re.MULTILINE,
            )
        with open(env_path, "w") as f:
            f.write(env_text)

    # Update the live settings object (takes effect until next restart)
    settings.re_valuation_provider = data.provider
    if data.api_key is not None:
        settings.re_valuation_api_key = data.api_key

    return ValuationConfigResponse(
        provider=settings.re_valuation_provider,
        has_api_key=bool(settings.re_valuation_api_key),
    )
