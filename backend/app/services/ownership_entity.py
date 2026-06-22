from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt
from app.core.visibility import VisibilityContext
from app.repositories.ownership_entity import OwnershipEntityRepository
from app.schemas.ownership_entity import OwnershipEntityResponse


class OwnershipEntityService:
    """Read access to a household's ownership entities (trusts / titling layer).
    Decrypts the AES-256-GCM `name_enc` field at read time.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OwnershipEntityRepository(session)

    async def list_entities(self, ctx: VisibilityContext) -> list[OwnershipEntityResponse]:
        entities = await self.repo.list_for_household(ctx.household_id)
        return [
            OwnershipEntityResponse(
                id=e.id,
                household_id=e.household_id,
                entity_type=e.entity_type,
                name=decrypt(e.name_enc),
                grantor_member_id=e.grantor_member_id,
                is_in_taxable_estate=e.is_in_taxable_estate,
                counts_in_personal_net_worth=e.counts_in_personal_net_worth,
                created_at=e.created_at,
            )
            for e in entities
        ]
