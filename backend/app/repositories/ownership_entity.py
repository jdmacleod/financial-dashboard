import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.ownership_entity import OwnershipEntity


class OwnershipEntityRepository:
    """Reads ownership entities for net-worth and estate-exposure aggregation.

    Ownership entities are not accounts, so they do not route through
    AccountRepository.get_visible; they are scoped by household_id and read
    alongside the already-visibility-filtered account list.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_map(self, household_id: uuid.UUID) -> dict[uuid.UUID, OwnershipEntity]:
        """Return {entity_id: OwnershipEntity} for the household."""
        result = await self.session.execute(
            select(OwnershipEntity).where(OwnershipEntity.household_id == household_id)
        )
        return {e.id: e for e in result.scalars().all()}

    async def list_for_household(self, household_id: uuid.UUID) -> list[OwnershipEntity]:
        """Return all ownership entities for the household, oldest first."""
        result = await self.session.execute(
            select(OwnershipEntity)
            .where(OwnershipEntity.household_id == household_id)
            .order_by(OwnershipEntity.created_at)
        )
        return list(result.scalars().all())


def counts_in_net_worth(account: Account, entity_map: dict[uuid.UUID, OwnershipEntity]) -> bool:
    """An account contributes to personal net worth when it is flagged
    include_in_net_worth AND it is not titled in an entity that sits outside
    personal net worth (ILIT/CRT/DAF-held). A missing entity row is treated
    as in-net-worth (fail open to the account's own flag).
    """
    if not account.include_in_net_worth:
        return False
    if account.ownership_entity_id is None:
        return True
    entity = entity_map.get(account.ownership_entity_id)
    return entity is None or entity.counts_in_personal_net_worth
