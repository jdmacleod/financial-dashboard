from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_session

bearer = HTTPBearer()


@dataclass(frozen=True)
class VisibilityContext:
    user_id: UUID
    member_id: UUID | None
    role: str  # 'primary' | 'partner' | 'dependent'
    household_id: UUID
    ip_address: str | None = None

    @property
    def is_primary(self) -> bool:
        return self.role == "primary"

    @property
    def can_export_executor(self) -> bool:
        return self.role == "primary"

    @property
    def can_write(self) -> bool:
        return self.role in ("primary", "partner")


async def _get_household_id(session: AsyncSession, user_id: UUID) -> UUID | None:
    from app.db.models.member import HouseholdMember
    from app.db.models.user import User

    result = await session.execute(
        select(HouseholdMember.household_id)
        .join(User, User.member_id == HouseholdMember.id)
        .where(User.id == user_id, User.is_active.is_(True))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_visibility_ctx(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> VisibilityContext:
    try:
        payload = decode_token(credentials.credentials, "access")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = UUID(payload["sub"])
    member_id = UUID(payload["member_id"]) if payload.get("member_id") else None
    role = payload.get("role", "partner")

    household_id = await _get_household_id(session, user_id)
    if not household_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    ip = request.client.host if request.client else None

    return VisibilityContext(
        user_id=user_id,
        member_id=member_id,
        role=role,
        household_id=household_id,
        ip_address=ip,
    )
