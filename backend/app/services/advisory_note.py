import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.advisory_note import AdvisoryNote
from app.db.models.ownership_entity import OwnershipEntity
from app.repositories.account import AccountRepository
from app.schemas.advisory_note import AdvisoryNoteCreate, AdvisoryNoteUpdate


class AdvisoryNoteService:
    """Read/write access to a household's advisory notes (planning insights
    surfaced in-app). Notes are household-scoped, optionally anchored to an
    account or ownership entity, and filterable by category.

    A note anchored to an account is only returned to contexts that can see
    that account: ``list_notes`` filters account-anchored notes through
    ``AccountRepository.get_visible`` so a dependent never sees a note attached
    to an account hidden from them (household-level and entity-anchored notes
    carry no account, so they remain visible).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)
        self.account_repo = AccountRepository(session)

    async def list_notes(
        self,
        ctx: VisibilityContext,
        *,
        account_id: uuid.UUID | None = None,
        ownership_entity_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> list[AdvisoryNote]:
        if account_id is not None:
            # Raises 404 if the account is not visible to this context.
            await self.account_repo.get_by_id(ctx, account_id)

        q = select(AdvisoryNote).where(AdvisoryNote.household_id == ctx.household_id)
        if account_id is not None:
            q = q.where(AdvisoryNote.account_id == account_id)
        if ownership_entity_id is not None:
            q = q.where(AdvisoryNote.ownership_entity_id == ownership_entity_id)
        if category is not None:
            q = q.where(AdvisoryNote.category == category)
        q = q.order_by(AdvisoryNote.created_at)
        notes = list((await self.session.execute(q)).scalars().all())

        # Security refinement: drop account-anchored notes whose account is not
        # visible to this context. A note with no account_id is household- or
        # entity-level and always visible.
        visible_ids = {a.id for a in await self.account_repo.get_visible(ctx)}
        return [n for n in notes if n.account_id is None or n.account_id in visible_ids]

    async def get_by_id(self, ctx: VisibilityContext, note_id: uuid.UUID) -> AdvisoryNote:
        result = await self.session.execute(
            select(AdvisoryNote).where(
                AdvisoryNote.id == note_id,
                AdvisoryNote.household_id == ctx.household_id,
            )
        )
        note = result.scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=404, detail="Advisory note not found")
        # An account-anchored note is only reachable if its account is visible.
        if note.account_id is not None:
            await self.account_repo.get_by_id(ctx, note.account_id)
        return note

    async def _validate_anchors(
        self,
        ctx: VisibilityContext,
        account_id: uuid.UUID | None,
        ownership_entity_id: uuid.UUID | None,
    ) -> None:
        if account_id is not None:
            await self.account_repo.get_by_id(ctx, account_id)
        if ownership_entity_id is not None:
            result = await self.session.execute(
                select(OwnershipEntity.id).where(
                    OwnershipEntity.id == ownership_entity_id,
                    OwnershipEntity.household_id == ctx.household_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(status_code=400, detail="ownership_entity_id not in household")

    @audit("advisory_note.created", "advisory_note")
    async def create(self, ctx: VisibilityContext, data: AdvisoryNoteCreate) -> AdvisoryNote:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await self._validate_anchors(ctx, data.account_id, data.ownership_entity_id)
        note = AdvisoryNote(
            household_id=ctx.household_id,
            account_id=data.account_id,
            ownership_entity_id=data.ownership_entity_id,
            category=data.category,
            title=data.title,
            body=data.body,
            created_at=datetime.now(UTC),
        )
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)
        return note

    @audit("advisory_note.updated", "advisory_note")
    async def update(
        self, ctx: VisibilityContext, note_id: uuid.UUID, data: AdvisoryNoteUpdate
    ) -> AdvisoryNote:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        note = await self.get_by_id(ctx, note_id)
        self._prev_snapshot = _snapshot(note)
        await self._validate_anchors(ctx, data.account_id, data.ownership_entity_id)
        if data.account_id is not None:
            note.account_id = data.account_id
        if data.ownership_entity_id is not None:
            note.ownership_entity_id = data.ownership_entity_id
        if data.category is not None:
            note.category = data.category
        if data.title is not None:
            note.title = data.title
        if data.body is not None:
            note.body = data.body
        await self.session.flush()
        await self.session.refresh(note)
        return note

    async def delete(self, ctx: VisibilityContext, note_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        note = await self.get_by_id(ctx, note_id)
        prev = _snapshot(note)
        await self.session.delete(note)
        await self.session.flush()
        await self.audit_repo.write(
            ctx=ctx,
            action="advisory_note.deleted",
            entity_type="advisory_note",
            entity_id=note_id,
            previous_value=prev,
        )
