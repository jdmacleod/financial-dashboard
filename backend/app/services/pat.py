import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository
from app.core.config import settings
from app.core.security import generate_pat, parse_pat, verify_pat_secret
from app.core.visibility import VisibilityContext
from app.db.models.personal_access_token import PersonalAccessToken


class PATService:
    """Issue, list, revoke, and authenticate personal access tokens.

    PAT lifecycle mutations are audited as auth events (``write_auth_event``),
    matching how auth.py records logins/password changes — and deliberately NOT
    via the @audit decorator, which snapshots a single returned entity and would
    both choke on the (token, model) tuple and risk logging the secret. The
    token_hash is also in AUDIT_SECRET_FIELDS as defense in depth.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def _active_count(self, household_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PersonalAccessToken)
            .where(
                PersonalAccessToken.household_id == household_id,
                PersonalAccessToken.revoked_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def create(
        self, ctx: VisibilityContext, label: str, expires_in_days: int | None = None
    ) -> tuple[PersonalAccessToken, str]:
        # Minting a programmatic write credential is primary-only: a partner can
        # write through the UI but should not be able to forge a long-lived API key.
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        if await self._active_count(ctx.household_id) >= settings.pat_max_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Maximum of {settings.pat_max_active} active tokens reached",
            )

        full, prefix, token_hash = generate_pat()
        now = datetime.now(UTC)
        ttl_days = expires_in_days or settings.pat_default_ttl_days
        pat = PersonalAccessToken(
            household_id=ctx.household_id,
            created_by=ctx.user_id,
            prefix=prefix,
            token_hash=token_hash,
            label=label,
            capability="import-write",
            created_at=now,
            expires_at=now + timedelta(days=ttl_days),
        )
        self.session.add(pat)
        await self.session.flush()
        await self.session.refresh(pat)

        await self.audit_repo.write_auth_event(
            household_id=ctx.household_id,
            user_id=ctx.user_id,
            action="pat.created",
            ip_address=ctx.ip_address,
            new_value={"label": label, "prefix": prefix, "capability": "import-write"},
            entity_id=pat.id,
        )
        await self.session.commit()
        return pat, full

    async def list(self, ctx: VisibilityContext) -> list[PersonalAccessToken]:
        result = await self.session.execute(
            select(PersonalAccessToken)
            .where(PersonalAccessToken.household_id == ctx.household_id)
            .order_by(PersonalAccessToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, ctx: VisibilityContext, pat_id: uuid.UUID) -> None:
        if not ctx.is_primary:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        result = await self.session.execute(
            select(PersonalAccessToken).where(
                PersonalAccessToken.id == pat_id,
                PersonalAccessToken.household_id == ctx.household_id,
            )
        )
        pat = result.scalar_one_or_none()
        if pat is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
        if pat.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Token already revoked"
            )
        pat.revoked_at = datetime.now(UTC)
        await self.audit_repo.write_auth_event(
            household_id=ctx.household_id,
            user_id=ctx.user_id,
            action="pat.revoked",
            ip_address=ctx.ip_address,
            new_value={"prefix": pat.prefix, "label": pat.label},
            entity_id=pat.id,
        )
        await self.session.commit()

    async def authenticate(self, token: str) -> PersonalAccessToken | None:
        """Resolve a presented PAT to its row, or None if invalid/expired/revoked.

        Live checks (re-read every request): hash match, not revoked, not expired.
        Updates last_used_at on success. The caller resolves the owning user's
        live role/active state separately, so a demoted/deactivated owner loses
        the token's authority without needing the token revoked.
        """
        parsed = parse_pat(token)
        if parsed is None:
            return None
        prefix, secret = parsed
        result = await self.session.execute(
            select(PersonalAccessToken).where(PersonalAccessToken.prefix == prefix)
        )
        pat = result.scalar_one_or_none()
        if pat is None or not verify_pat_secret(secret, pat.token_hash):
            return None
        now = datetime.now(UTC)
        if pat.revoked_at is not None:
            return None
        if pat.expires_at is not None and pat.expires_at <= now:
            return None
        pat.last_used_at = now
        await self.session.flush()
        return pat
