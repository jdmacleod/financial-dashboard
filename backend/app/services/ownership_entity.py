import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.encryption import decrypt, encrypt
from app.core.visibility import VisibilityContext
from app.db.models.member import HouseholdMember
from app.db.models.ownership_entity import OwnershipEntity
from app.repositories.ownership_entity import OwnershipEntityRepository
from app.schemas.ownership_entity import (
    OwnershipEntityCreate,
    OwnershipEntityResponse,
    OwnershipEntityUpdate,
)


class OwnershipEntityService:
    """Read/write access to a household's ownership entities (trusts / titling
    layer). The AES-256-GCM `name_enc` field is decrypted at read time and
    encrypted on write; it is excluded from the audit snapshot (CLAUDE.md #4).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = OwnershipEntityRepository(session)
        self.audit_repo = AuditRepository(session)

    @staticmethod
    def to_response(e: OwnershipEntity) -> OwnershipEntityResponse:
        return OwnershipEntityResponse(
            id=e.id,
            household_id=e.household_id,
            entity_type=e.entity_type,
            name=decrypt(e.name_enc),
            grantor_member_id=e.grantor_member_id,
            is_in_taxable_estate=e.is_in_taxable_estate,
            counts_in_personal_net_worth=e.counts_in_personal_net_worth,
            created_at=e.created_at,
        )

    async def list_entities(self, ctx: VisibilityContext) -> list[OwnershipEntityResponse]:
        entities = await self.repo.list_for_household(ctx.household_id)
        return [self.to_response(e) for e in entities]

    async def get_by_id(self, ctx: VisibilityContext, entity_id: uuid.UUID) -> OwnershipEntity:
        result = await self.session.execute(
            select(OwnershipEntity).where(
                OwnershipEntity.id == entity_id,
                OwnershipEntity.household_id == ctx.household_id,
            )
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            raise HTTPException(status_code=404, detail="Ownership entity not found")
        return entity

    async def _validate_member(self, ctx: VisibilityContext, member_id: uuid.UUID | None) -> None:
        if member_id is None:
            return
        result = await self.session.execute(
            select(HouseholdMember.id).where(
                HouseholdMember.id == member_id,
                HouseholdMember.household_id == ctx.household_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=400, detail="grantor_member_id not in household")

    @audit("ownership_entity.created", "ownership_entity")
    async def create(self, ctx: VisibilityContext, data: OwnershipEntityCreate) -> OwnershipEntity:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self._validate_member(ctx, data.grantor_member_id)
        entity = OwnershipEntity(
            household_id=ctx.household_id,
            entity_type=data.entity_type,
            name_enc=encrypt(data.name),
            grantor_member_id=data.grantor_member_id,
            is_in_taxable_estate=data.is_in_taxable_estate,
            counts_in_personal_net_worth=data.counts_in_personal_net_worth,
            created_at=datetime.now(UTC),
        )
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    @audit("ownership_entity.updated", "ownership_entity")
    async def update(
        self, ctx: VisibilityContext, entity_id: uuid.UUID, data: OwnershipEntityUpdate
    ) -> OwnershipEntity:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        entity = await self.get_by_id(ctx, entity_id)
        self._prev_snapshot = _snapshot(entity, exclude=AUDIT_EXCLUDED_FIELDS)
        if data.entity_type is not None:
            entity.entity_type = data.entity_type
        if data.name is not None:
            entity.name_enc = encrypt(data.name)
        if data.grantor_member_id is not None:
            await self._validate_member(ctx, data.grantor_member_id)
            entity.grantor_member_id = data.grantor_member_id
        if data.is_in_taxable_estate is not None:
            entity.is_in_taxable_estate = data.is_in_taxable_estate
        if data.counts_in_personal_net_worth is not None:
            entity.counts_in_personal_net_worth = data.counts_in_personal_net_worth
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, ctx: VisibilityContext, entity_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        entity = await self.get_by_id(ctx, entity_id)
        prev = _snapshot(entity, exclude=AUDIT_EXCLUDED_FIELDS)
        await self.session.delete(entity)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="ownership_entity.deleted",
            entity_type="ownership_entity",
            entity_id=entity_id,
            previous_value=prev,
        )
