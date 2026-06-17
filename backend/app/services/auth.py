import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_reauth_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.models.member import HouseholdMember
from app.db.models.user import User


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def _get_household_id(self, user: User) -> uuid.UUID | None:
        if not user.member_id:
            return None
        result = await self.session.execute(
            select(HouseholdMember.household_id).where(HouseholdMember.id == user.member_id)
        )
        return result.scalar_one_or_none()

    async def login(self, email: str, password: str, ip_address: str | None) -> tuple[str, str]:
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        household_id = await self._get_household_id(user) if user else None

        if not user or not user.is_active:
            if user and household_id:
                await self.audit_repo.write_auth_event(
                    household_id=household_id,
                    user_id=user.id,
                    action="auth.login_failed",
                    ip_address=ip_address,
                )
                await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Check lockout
        if user.locked_until and user.locked_until > datetime.now(UTC):
            seconds_remaining = (user.locked_until - datetime.now(UTC)).total_seconds()
            minutes_remaining = int(seconds_remaining // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "message": "Account locked",
                    "locked_until": user.locked_until.isoformat(),
                    "minutes_remaining": minutes_remaining,
                },
            )

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_login_attempts:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.lockout_minutes)
                await self.session.flush()
                if household_id:
                    await self.audit_repo.write_auth_event(
                        household_id=household_id,
                        user_id=user.id,
                        action="auth.account_locked",
                        ip_address=ip_address,
                        new_value={"failed_attempt_count": user.failed_login_attempts},
                    )
            else:
                await self.session.flush()
                if household_id:
                    await self.audit_repo.write_auth_event(
                        household_id=household_id,
                        user_id=user.id,
                        action="auth.login_failed",
                        ip_address=ip_address,
                    )
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now(UTC)

        member_result = await self.session.execute(
            select(HouseholdMember).where(HouseholdMember.id == user.member_id)
        )
        member = member_result.scalar_one_or_none()
        role = member.role if member else "partner"

        access_token = create_access_token(
            str(user.id), str(user.member_id) if user.member_id else None, role
        )
        refresh_token = create_refresh_token(str(user.id))
        user.refresh_token_hash = _hash_refresh_token(refresh_token)

        await self.session.flush()
        if household_id:
            await self.audit_repo.write_auth_event(
                household_id=household_id,
                user_id=user.id,
                action="auth.login_success",
                ip_address=ip_address,
            )
        await self.session.commit()
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        try:
            payload = decode_token(refresh_token, "refresh")
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc

        user_id = uuid.UUID(payload["sub"])
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        if not user.refresh_token_hash or user.refresh_token_hash != _hash_refresh_token(
            refresh_token
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        member_result = await self.session.execute(
            select(HouseholdMember).where(HouseholdMember.id == user.member_id)
        )
        member = member_result.scalar_one_or_none()
        role = member.role if member else "partner"

        new_access = create_access_token(
            str(user.id), str(user.member_id) if user.member_id else None, role
        )
        new_refresh = create_refresh_token(str(user.id))
        user.refresh_token_hash = _hash_refresh_token(new_refresh)

        await self.session.commit()
        return new_access, new_refresh

    async def logout(
        self, user_id: uuid.UUID, household_id: uuid.UUID, ip_address: str | None
    ) -> None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.refresh_token_hash = None
            await self.session.flush()
            await self.audit_repo.write_auth_event(
                household_id=household_id,
                user_id=user_id,
                action="auth.logout",
                ip_address=ip_address,
            )
            await self.session.commit()

    async def reauth(
        self, user_id: uuid.UUID, password: str, household_id: uuid.UUID, ip_address: str | None
    ) -> str:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        token = create_reauth_token(str(user.id))
        await self.audit_repo.write_auth_event(
            household_id=household_id,
            user_id=user_id,
            action="auth.executor_reauth_success",
            ip_address=ip_address,
        )
        await self.session.commit()
        return token

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
        household_id: uuid.UUID,
        ip_address: str | None,
    ) -> None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password"
            )

        user.hashed_password = hash_password(new_password)
        user.last_password_change = datetime.now(UTC)
        user.refresh_token_hash = None  # invalidate existing sessions
        await self.session.flush()
        await self.audit_repo.write_auth_event(
            household_id=household_id,
            user_id=user_id,
            action="auth.password_changed",
            ip_address=ip_address,
        )
        await self.session.commit()
