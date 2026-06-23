import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.insurance_policy import InsurancePolicy
from app.db.models.member import HouseholdMember
from app.db.models.ownership_entity import OwnershipEntity
from app.db.models.real_estate import RealEstateProperty
from app.repositories.account import AccountRepository
from app.schemas.insurance_policy import InsurancePolicyCreate, InsurancePolicyUpdate


class InsurancePolicyService:
    """Read/write access to a household's insurance policies (umbrella, life, DI,
    LTC, scheduled/specialty). Household-scoped, no encrypted fields.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    async def list_policies(self, ctx: VisibilityContext) -> list[InsurancePolicy]:
        result = await self.session.execute(
            select(InsurancePolicy)
            .where(InsurancePolicy.household_id == ctx.household_id)
            .order_by(InsurancePolicy.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, ctx: VisibilityContext, policy_id: uuid.UUID) -> InsurancePolicy:
        result = await self.session.execute(
            select(InsurancePolicy).where(
                InsurancePolicy.id == policy_id,
                InsurancePolicy.household_id == ctx.household_id,
            )
        )
        policy = result.scalar_one_or_none()
        if policy is None:
            raise HTTPException(status_code=404, detail="Insurance policy not found")
        return policy

    async def _validate_refs(
        self,
        ctx: VisibilityContext,
        insured_member_id: uuid.UUID | None,
        owner_ownership_entity_id: uuid.UUID | None,
        cash_value_account_id: uuid.UUID | None,
        insured_real_estate_id: uuid.UUID | None = None,
    ) -> None:
        if insured_member_id is not None:
            result = await self.session.execute(
                select(HouseholdMember.id).where(
                    HouseholdMember.id == insured_member_id,
                    HouseholdMember.household_id == ctx.household_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(status_code=400, detail="insured_member_id not in household")
        if owner_ownership_entity_id is not None:
            result = await self.session.execute(
                select(OwnershipEntity.id).where(
                    OwnershipEntity.id == owner_ownership_entity_id,
                    OwnershipEntity.household_id == ctx.household_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=400, detail="owner_ownership_entity_id not in household"
                )
        if cash_value_account_id is not None:
            await self.account_repo.get_by_id(ctx, cash_value_account_id)
        if insured_real_estate_id is not None:
            result = await self.session.execute(
                select(RealEstateProperty.id)
                .join(Account, RealEstateProperty.account_id == Account.id)
                .where(
                    RealEstateProperty.id == insured_real_estate_id,
                    Account.household_id == ctx.household_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=400, detail="insured_real_estate_id not in household"
                )

    @audit("insurance_policy.created", "insurance_policy")
    async def create(self, ctx: VisibilityContext, data: InsurancePolicyCreate) -> InsurancePolicy:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self._validate_refs(
            ctx,
            data.insured_member_id,
            data.owner_ownership_entity_id,
            data.cash_value_account_id,
            data.insured_real_estate_id,
        )
        policy = InsurancePolicy(
            household_id=ctx.household_id,
            policy_type=data.policy_type,
            insured_member_id=data.insured_member_id,
            owner_ownership_entity_id=data.owner_ownership_entity_id,
            coverage_amount=data.coverage_amount,
            premium_amount=data.premium_amount,
            premium_cadence=data.premium_cadence,
            cash_value_account_id=data.cash_value_account_id,
            carrier=data.carrier,
            policy_number=data.policy_number,
            technical_notes=data.technical_notes,
            insured_real_estate_id=data.insured_real_estate_id,
            policy_metadata=data.metadata,
            created_at=datetime.now(UTC),
        )
        self.session.add(policy)
        await self.session.flush()
        await self.session.refresh(policy)
        return policy

    @audit("insurance_policy.updated", "insurance_policy")
    async def update(
        self, ctx: VisibilityContext, policy_id: uuid.UUID, data: InsurancePolicyUpdate
    ) -> InsurancePolicy:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        policy = await self.get_by_id(ctx, policy_id)
        self._prev_snapshot = _snapshot(policy)
        await self._validate_refs(
            ctx,
            data.insured_member_id,
            data.owner_ownership_entity_id,
            data.cash_value_account_id,
            data.insured_real_estate_id,
        )
        if data.policy_type is not None:
            policy.policy_type = data.policy_type
        if data.insured_member_id is not None:
            policy.insured_member_id = data.insured_member_id
        if data.owner_ownership_entity_id is not None:
            policy.owner_ownership_entity_id = data.owner_ownership_entity_id
        if data.coverage_amount is not None:
            policy.coverage_amount = data.coverage_amount
        if data.premium_amount is not None:
            policy.premium_amount = data.premium_amount
        if data.premium_cadence is not None:
            policy.premium_cadence = data.premium_cadence
        if data.cash_value_account_id is not None:
            policy.cash_value_account_id = data.cash_value_account_id
        if data.carrier is not None:
            policy.carrier = data.carrier
        if data.policy_number is not None:
            policy.policy_number = data.policy_number
        if data.technical_notes is not None:
            policy.technical_notes = data.technical_notes
        if data.insured_real_estate_id is not None:
            policy.insured_real_estate_id = data.insured_real_estate_id
        if data.metadata is not None:
            policy.policy_metadata = data.metadata
        await self.session.flush()
        await self.session.refresh(policy)
        return policy

    async def delete(self, ctx: VisibilityContext, policy_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        policy = await self.get_by_id(ctx, policy_id)
        prev = _snapshot(policy)
        await self.session.delete(policy)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="insurance_policy.deleted",
            entity_type="insurance_policy",
            entity_id=policy_id,
            previous_value=prev,
        )
