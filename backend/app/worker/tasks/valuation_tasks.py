from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.encryption import decrypt
from app.db.models.property_valuation import PropertyValuation
from app.db.models.real_estate import RealEstateProperty

logger = logging.getLogger(__name__)


async def _fetch_all_properties(session: AsyncSession) -> list[RealEstateProperty]:
    result = await session.execute(select(RealEstateProperty))
    return list(result.scalars().all())


async def _create_valuation(
    session: AsyncSession,
    property_id: Any,
    estimated_value: Decimal,
    source: str,
    confidence_score: Decimal | None = None,
) -> None:
    valuation = PropertyValuation(
        real_estate_property_id=property_id,
        valuation_date=date.today(),
        estimated_value=estimated_value,
        source=source,
        confidence_score=confidence_score,
        created_at=datetime.now(UTC),
    )
    session.add(valuation)
    await session.flush()


async def _get_estimate_attom(address: str) -> tuple[Decimal, Decimal | None]:
    """Call ATTOM API. Returns (estimated_value, confidence_score)."""
    import httpx

    api_key = settings.re_valuation_api_key
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.gateway.attomdata.com/propertyapi/v1.0.0/avm/detail",
            params={"address1": address},
            headers={"apikey": api_key, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        avm = data["property"][0]["avm"]
        value = Decimal(str(avm["amount"]["value"]))
        score = Decimal(str(avm.get("score", 0))) / 100 if avm.get("score") else None
        return value, score


async def _get_estimate_estated(address: str) -> tuple[Decimal, Decimal | None]:
    """Call Estated API. Returns (estimated_value, confidence_score)."""
    import httpx

    api_key = settings.re_valuation_api_key
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://apis.estated.com/v4/property",
            params={"token": api_key, "combined_input": address},
        )
        resp.raise_for_status()
        data = resp.json()
        value = Decimal(str(data["data"]["valuation"]["value"]))
        return value, None


async def refresh_valuations(ctx: dict[str, Any]) -> None:
    """ARQ task: refresh real estate valuations from the configured provider."""
    provider = settings.re_valuation_provider
    if provider == "manual":
        logger.info("Valuation provider is 'manual' — skipping automatic refresh")
        return

    session_factory = ctx["db"]
    async with session_factory() as session:
        properties = await _fetch_all_properties(session)
        if not properties:
            logger.info("No real estate properties found — skipping valuation refresh")
            return

        refreshed = 0
        for prop in properties:
            try:
                address = decrypt(prop.address_enc)
                if provider == "attom":
                    value, confidence = await _get_estimate_attom(address)
                    source = "api_attom"
                elif provider == "estated":
                    value, confidence = await _get_estimate_estated(address)
                    source = "api_estated"
                else:
                    logger.warning("Unknown valuation provider: %s", provider)
                    continue

                await _create_valuation(session, prop.id, value, source, confidence)
                refreshed += 1
            except Exception as exc:
                logger.warning("Valuation refresh failed for property %s: %s", prop.id, exc)

        await session.commit()
        logger.info(
            "Valuation refresh complete: %d/%d properties updated",
            refreshed,
            len(properties),
        )
