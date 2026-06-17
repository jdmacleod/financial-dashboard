import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS, AuditRepository, _snapshot, audit
from app.core.security import hash_password
from app.core.visibility import VisibilityContext
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @audit("user.created", "user")
    async def create(self, ctx: VisibilityContext, data: UserCreate) -> User:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        existing = await self.session.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        now = datetime.now(UTC)
        user = User(
            member_id=data.member_id,
            email=data.email,
            hashed_password=hash_password(data.password),
            is_active=True,
            failed_login_attempts=0,
            last_password_change=now,
            created_at=now,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    @audit("user.updated", "user")
    async def update(self, ctx: VisibilityContext, user_id: uuid.UUID, data: UserUpdate) -> User:
        if user_id != ctx.user_id and not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        user = await self.get_by_id(user_id)
        self._prev_snapshot = _snapshot(user, exclude=AUDIT_EXCLUDED_FIELDS)

        if data.email is not None:
            user.email = data.email
        if data.is_active is not None:
            if not ctx.is_primary:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            user.is_active = data.is_active
        await self.session.flush()
        await self.session.refresh(user)
        return user

    @audit("user.deactivated", "user")
    async def deactivate(self, ctx: VisibilityContext, user_id: uuid.UUID) -> User:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        user = await self.get_by_id(user_id)
        self._prev_snapshot = _snapshot(user, exclude=AUDIT_EXCLUDED_FIELDS)
        user.is_active = False
        user.refresh_token_hash = None
        await self.session.flush()
        await self.session.refresh(user)
        return user
