from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import throttle
from app.core.security import PAT_PREFIX, decode_token
from app.db.base import get_session

bearer = HTTPBearer()


@dataclass(frozen=True)
class VisibilityContext:
    user_id: UUID
    member_id: UUID | None
    role: str  # 'primary' | 'partner' | 'dependent'
    household_id: UUID
    ip_address: str | None = None
    # How the request authenticated: 'session' (browser JWT) or 'pat'
    # (programmatic personal access token). PAT-minted contexts carry the
    # token's capability so a route can require it; session contexts don't.
    auth_method: str = "session"
    capability: str | None = None

    @property
    def is_primary(self) -> bool:
        return self.role == "primary"

    @property
    def can_export_executor(self) -> bool:
        return self.role == "primary"

    @property
    def can_write(self) -> bool:
        return self.role in ("primary", "partner")


async def _resolve_identity(session: AsyncSession, user_id: UUID) -> tuple[UUID, UUID, str] | None:
    """Return (household_id, member_id, role) for a live, active user.

    Single source of truth for both the JWT and PAT paths: role and household
    are read from the DB, not trusted from a token payload. This closes the
    stale-role gap (a JWT carried role for up to 30 minutes after a demotion) and
    makes inactive-user rejection free for PATs.
    """
    from app.db.models.member import HouseholdMember
    from app.db.models.user import User

    result = await session.execute(
        select(HouseholdMember.household_id, HouseholdMember.id, HouseholdMember.role)
        .join(User, User.member_id == HouseholdMember.id)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            HouseholdMember.is_active.is_(True),
        )
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    return row[0], row[1], row[2]


async def _ctx_from_pat(request: Request, token: str, session: AsyncSession) -> VisibilityContext:
    from app.services.pat import PATService

    ip = request.client.host if request.client else None
    if throttle.is_throttled(ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)

    pat = await PATService(session).authenticate(token)
    if pat is None:
        # A bad token can't be attributed to a household, so there's nothing to
        # audit; the IP throttle counter is the abuse signal.
        throttle.record_failure(ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    identity = await _resolve_identity(session, pat.created_by)
    if identity is None:
        # Owner deactivated/removed since the token was minted → token is dead.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    throttle.clear(ip)
    household_id, member_id, role = identity
    return VisibilityContext(
        user_id=pat.created_by,
        member_id=member_id,
        role=role,
        household_id=household_id,
        ip_address=ip,
        auth_method="pat",
        capability=pat.capability,
    )


async def _ctx_from_jwt(request: Request, token: str, session: AsyncSession) -> VisibilityContext:
    try:
        payload = decode_token(token, "access")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from exc

    user_id = UUID(payload["sub"])
    identity = await _resolve_identity(session, user_id)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    household_id, member_id, role = identity
    ip = request.client.host if request.client else None
    return VisibilityContext(
        user_id=user_id,
        member_id=member_id,
        role=role,
        household_id=household_id,
        ip_address=ip,
        auth_method="session",
        capability=None,
    )


async def get_visibility_ctx(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> VisibilityContext:
    """Resolve a request to a VisibilityContext from EITHER a JWT or a PAT.

    Routing is deterministic by the token's structured prefix — no guess-and-
    fallback. A ``hl_pat_`` credential takes the PAT path; anything else is
    treated as a session JWT.
    """
    token = credentials.credentials
    if token.startswith(PAT_PREFIX):
        return await _ctx_from_pat(request, token, session)
    return await _ctx_from_jwt(request, token, session)


async def require_session_ctx(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
) -> VisibilityContext:
    """Reject PAT auth. For surfaces a programmatic token must never reach —
    e.g. minting/revoking tokens (a PAT issuing PATs is privilege escalation)."""
    if ctx.auth_method != "session":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an interactive session",
        )
    return ctx


async def require_import_write_ctx(
    ctx: VisibilityContext = Depends(get_visibility_ctx),
) -> VisibilityContext:
    """Allow a session writer (primary/partner) OR a PAT with the import-write
    capability. The shared gate for the ingest staging endpoint."""
    if ctx.auth_method == "pat":
        if ctx.capability != "import-write":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return ctx
    if not ctx.can_write:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return ctx
