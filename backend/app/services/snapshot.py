import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.snapshot import AccountSnapshot
from app.repositories.account import AccountRepository
from app.schemas.snapshot import SnapshotCreate, SnapshotUpdate


class SnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.audit_repo = AuditRepository(session)

    async def list_snapshots(
        self, ctx: VisibilityContext, account_id: uuid.UUID
    ) -> list[AccountSnapshot]:
        await self.account_repo.get_by_id(ctx, account_id)
        result = await self.session.execute(
            select(AccountSnapshot)
            .where(AccountSnapshot.account_id == account_id)
            .order_by(AccountSnapshot.snapshot_date.desc())
        )
        return list(result.scalars().all())

    async def _get_or_404(
        self, ctx: VisibilityContext, account_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> AccountSnapshot:
        await self.account_repo.get_by_id(ctx, account_id)
        result = await self.session.execute(
            select(AccountSnapshot).where(
                AccountSnapshot.id == snapshot_id, AccountSnapshot.account_id == account_id
            )
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
        return snapshot

    @audit("snapshot.created", "account_snapshot")
    async def create(
        self, ctx: VisibilityContext, account_id: uuid.UUID, data: SnapshotCreate
    ) -> AccountSnapshot:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self.account_repo.get_by_id(ctx, account_id)
        snapshot = AccountSnapshot(
            account_id=account_id,
            snapshot_date=data.snapshot_date,
            balance=data.balance,
            contributed_ytd=data.contributed_ytd,
            employer_match_ytd=data.employer_match_ytd,
            memo=data.memo,
            source="manual",
            created_at=datetime.now(UTC),
        )
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    @audit("snapshot.updated", "account_snapshot")
    async def update(
        self,
        ctx: VisibilityContext,
        account_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        data: SnapshotUpdate,
    ) -> AccountSnapshot:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        snapshot = await self._get_or_404(ctx, account_id, snapshot_id)
        self._prev_snapshot = _snapshot(snapshot)

        if data.balance is not None:
            snapshot.balance = data.balance
        if data.contributed_ytd is not None:
            snapshot.contributed_ytd = data.contributed_ytd
        if data.employer_match_ytd is not None:
            snapshot.employer_match_ytd = data.employer_match_ytd
        if data.memo is not None:
            snapshot.memo = data.memo

        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def delete(
        self, ctx: VisibilityContext, account_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        snapshot = await self._get_or_404(ctx, account_id, snapshot_id)
        prev = _snapshot(snapshot)
        await self.session.delete(snapshot)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="snapshot.deleted",
            entity_type="account_snapshot",
            entity_id=snapshot_id,
            previous_value=prev,
        )
