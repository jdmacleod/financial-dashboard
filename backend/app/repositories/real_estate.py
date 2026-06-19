import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.property_valuation import PropertyValuation
from app.db.models.real_estate import RealEstateProperty


class RealEstateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, property_id: uuid.UUID) -> RealEstateProperty | None:
        result = await self.session.execute(
            select(RealEstateProperty).where(RealEstateProperty.id == property_id)
        )
        return result.scalar_one_or_none()

    async def get_by_account_id(self, account_id: uuid.UUID) -> RealEstateProperty | None:
        result = await self.session.execute(
            select(RealEstateProperty).where(RealEstateProperty.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def list_for_accounts(self, account_ids: list[uuid.UUID]) -> list[RealEstateProperty]:
        if not account_ids:
            return []
        result = await self.session.execute(
            select(RealEstateProperty).where(RealEstateProperty.account_id.in_(account_ids))
        )
        return list(result.scalars().all())

    async def list_valuations(self, property_id: uuid.UUID) -> list[PropertyValuation]:
        result = await self.session.execute(
            select(PropertyValuation)
            .where(PropertyValuation.real_estate_property_id == property_id)
            .order_by(PropertyValuation.valuation_date.desc())
        )
        return list(result.scalars().all())

    async def latest_valuation(self, property_id: uuid.UUID) -> PropertyValuation | None:
        result = await self.session.execute(
            select(PropertyValuation)
            .where(PropertyValuation.real_estate_property_id == property_id)
            .order_by(PropertyValuation.valuation_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def latest_valuation_as_of(
        self, property_id: uuid.UUID, as_of: date
    ) -> PropertyValuation | None:
        result = await self.session.execute(
            select(PropertyValuation)
            .where(
                PropertyValuation.real_estate_property_id == property_id,
                PropertyValuation.valuation_date <= as_of,
            )
            .order_by(PropertyValuation.valuation_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def batch_latest_valuations_as_of(
        self, property_ids: list[uuid.UUID], as_of: date
    ) -> dict[uuid.UUID, Decimal]:
        """Return {property_id: estimated_value} for the latest valuation ≤ as_of per property."""
        if not property_ids:
            return {}
        subq = (
            select(
                PropertyValuation.real_estate_property_id,
                func.max(PropertyValuation.valuation_date).label("max_date"),
            )
            .where(
                PropertyValuation.real_estate_property_id.in_(property_ids),
                PropertyValuation.valuation_date <= as_of,
            )
            .group_by(PropertyValuation.real_estate_property_id)
            .subquery()
        )
        result = await self.session.execute(
            select(
                PropertyValuation.real_estate_property_id,
                PropertyValuation.estimated_value,
            ).join(
                subq,
                (PropertyValuation.real_estate_property_id == subq.c.real_estate_property_id)
                & (PropertyValuation.valuation_date == subq.c.max_date),
            )
        )
        return {row[0]: row[1] for row in result.all()}
