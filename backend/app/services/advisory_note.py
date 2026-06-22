import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.advisory_note import AdvisoryNote


class AdvisoryNoteService:
    """Read access to a household's advisory notes (planning insights surfaced
    in-app). Notes are household-scoped, optionally anchored to an account or
    ownership entity, and filterable by category.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_notes(
        self,
        ctx: VisibilityContext,
        *,
        account_id: uuid.UUID | None = None,
        ownership_entity_id: uuid.UUID | None = None,
        category: str | None = None,
    ) -> list[AdvisoryNote]:
        q = select(AdvisoryNote).where(AdvisoryNote.household_id == ctx.household_id)
        if account_id is not None:
            q = q.where(AdvisoryNote.account_id == account_id)
        if ownership_entity_id is not None:
            q = q.where(AdvisoryNote.ownership_entity_id == ownership_entity_id)
        if category is not None:
            q = q.where(AdvisoryNote.category == category)
        q = q.order_by(AdvisoryNote.created_at)
        result = await self.session.execute(q)
        return list(result.scalars().all())
