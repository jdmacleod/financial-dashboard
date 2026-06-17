import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def create(self, data: UserCreate) -> User:
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

    async def update(
        self, user_id: uuid.UUID, data: UserUpdate, requesting_user_id: uuid.UUID, is_primary: bool
    ) -> User:
        if user_id != requesting_user_id and not is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        user = await self.get_by_id(user_id)
        if data.email is not None:
            user.email = data.email
        if data.is_active is not None:
            if not is_primary:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
            user.is_active = data.is_active
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def deactivate(self, user_id: uuid.UUID, is_primary: bool) -> User:
        if not is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        user = await self.get_by_id(user_id)
        user.is_active = False
        user.refresh_token_hash = None
        await self.session.flush()
        await self.session.refresh(user)
        return user
