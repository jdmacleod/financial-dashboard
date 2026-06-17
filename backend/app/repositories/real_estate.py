import uuid

from sqlalchemy import select
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
