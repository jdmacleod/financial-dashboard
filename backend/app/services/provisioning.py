import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot
from app.core.security import generate_temporary_password, hash_password
from app.core.visibility import VisibilityContext
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.provisioning import ProvisionRequest


@dataclass
class ProvisionResult:
    member: HouseholdMember
    user: User
    temporary_password: str


class ProvisionService:
    """Adds a login-capable household member in one action.

    A primary or partner provisions a member + user with a server-generated
    temporary password; the user is forced to set their own on first login
    (``must_change_password``). This does NOT reuse MemberService.create /
    UserService.create because those gate on ``ctx.is_primary`` — provisioning
    is allowed for partners too — so it inserts both rows itself under a
    ``can_write`` gate plus a role-escalation guard, and writes the audit rows
    manually. The temporary password is hashed at rest and never audited.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def provision(self, ctx: VisibilityContext, data: ProvisionRequest) -> ProvisionResult:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        # Privilege-escalation guard: only a primary may mint another primary.
        if data.role == "primary" and not ctx.is_primary:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a primary can add another primary.",
            )
        # Email uniqueness — fail early and clearly, not as a late DB error.
        existing = await self.session.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That email already has a login.",
            )

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

        temporary_password = generate_temporary_password()
        user = User(
            member_id=member.id,
            email=data.email,
            hashed_password=hash_password(temporary_password),
            is_active=True,
            failed_login_attempts=0,
            last_password_change=now,
            must_change_password=True,
            created_at=now,
        )
        self.session.add(user)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="member.created",
            entity_type="member",
            entity_id=member.id,
            new_value=_snapshot(member),
        )
        await self.audit_repo.write(
            ctx=ctx,
            action="user.provisioned",
            entity_type="user",
            entity_id=user.id,
            new_value=_snapshot(user, exclude=AUDIT_EXCLUDED_FIELDS),
        )
        await self.session.refresh(member)
        await self.session.refresh(user)
        return ProvisionResult(member=member, user=user, temporary_password=temporary_password)

    async def regenerate_temporary_password(
        self, ctx: VisibilityContext, user_id: uuid.UUID
    ) -> str:
        """Re-issue a temporary password for a user who has not yet set their own.

        Guarded to ``must_change_password`` users so an inviter can't silently
        reset the password of an established member. Returns the new plaintext
        once; the old one stops working.
        """
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        result = await self.session.execute(
            select(User)
            .join(HouseholdMember, HouseholdMember.id == User.member_id)
            .where(User.id == user_id, HouseholdMember.household_id == ctx.household_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user has already set their own password.",
            )
        temporary_password = generate_temporary_password()
        user.hashed_password = hash_password(temporary_password)
        user.last_password_change = datetime.now(UTC)
        user.refresh_token_hash = None
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="user.temp_password_regenerated",
            entity_type="user",
            entity_id=user.id,
        )
        return temporary_password
