import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.member import HouseholdMember
from app.schemas.member import MemberCreate, MemberUpdate


class MemberService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def list_members(self, ctx: VisibilityContext) -> list[HouseholdMember]:
        result = await self.session.execute(
            select(HouseholdMember).where(HouseholdMember.household_id == ctx.household_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, ctx: VisibilityContext, member_id: uuid.UUID) -> HouseholdMember:
        result = await self.session.execute(
            select(HouseholdMember).where(
                HouseholdMember.id == member_id,
                HouseholdMember.household_id == ctx.household_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return member

    @audit("member.created", "member")
    async def create(self, ctx: VisibilityContext, data: MemberCreate) -> HouseholdMember:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        now = datetime.now(UTC)
        member = HouseholdMember(
            household_id=ctx.household_id,
            display_name=data.display_name,
            role=data.role,
            date_of_birth=data.date_of_birth,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    @audit("member.updated", "member")
    async def update(
        self, ctx: VisibilityContext, member_id: uuid.UUID, data: MemberUpdate
    ) -> HouseholdMember:
        # Self-or-primary: a primary may edit any member; anyone else may edit
        # only their own record (CEO-review Decision 3, self-service profile).
        is_self = ctx.member_id is not None and member_id == ctx.member_id
        if not ctx.is_primary and not is_self:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        member = await self.get_by_id(ctx, member_id)

        # Role and activation remain primary-only, even when editing yourself —
        # a member can't promote themselves or deactivate their own account.
        if not ctx.is_primary:
            if data.role is not None and data.role != member.role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a primary member can change roles",
                )
            if data.is_active is not None and data.is_active != member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only a primary member can change activation",
                )

        self._prev_snapshot = _snapshot(member, exclude=AUDIT_EXCLUDED_FIELDS)

        # Prevent downgrading the last primary
        if data.role is not None and data.role != member.role and member.role == "primary":
            await self._check_not_last_primary(ctx, member_id)

        if data.display_name is not None:
            member.display_name = data.display_name
        if data.role is not None:
            member.role = data.role
        if data.date_of_birth is not None:
            member.date_of_birth = data.date_of_birth
        if data.is_active is not None:
            member.is_active = data.is_active

        member.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    @audit("member.deactivated", "member")
    async def deactivate(self, ctx: VisibilityContext, member_id: uuid.UUID) -> HouseholdMember:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        member = await self.get_by_id(ctx, member_id)
        self._prev_snapshot = _snapshot(member, exclude=AUDIT_EXCLUDED_FIELDS)
        await self._check_not_last_primary(ctx, member_id)
        member.is_active = False
        member.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def _check_not_last_primary(self, ctx: VisibilityContext, member_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(HouseholdMember).where(
                HouseholdMember.household_id == ctx.household_id,
                HouseholdMember.role == "primary",
                HouseholdMember.is_active.is_(True),
                HouseholdMember.id != member_id,
            )
        )
        others = result.scalars().all()
        if not others:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot deactivate or change role of the last primary member",
            )
