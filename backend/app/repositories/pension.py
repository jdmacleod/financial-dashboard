import uuid
from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionAccount, PensionEstimateHistory
from app.repositories.account import AccountRepository


class PensionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._account_repo = AccountRepository(session)

    async def get_by_account_id(self, account_id: uuid.UUID) -> PensionAccount | None:
        result = await self.session.execute(
            select(PensionAccount).where(PensionAccount.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, pension_id: uuid.UUID) -> PensionAccount | None:
        result = await self.session.execute(
            select(PensionAccount).where(PensionAccount.id == pension_id)
        )
        return result.scalar_one_or_none()

    async def get_by_account_ids(self, account_ids: list[uuid.UUID]) -> list[PensionAccount]:
        if not account_ids:
            return []
        result = await self.session.execute(
            select(PensionAccount).where(PensionAccount.account_id.in_(account_ids))
        )
        return list(result.scalars().all())

    async def get_estimate_history(
        self, pension_account_id: uuid.UUID
    ) -> list[PensionEstimateHistory]:
        """Estimate snapshots for one pension, oldest first."""
        result = await self.session.execute(
            select(PensionEstimateHistory)
            .where(PensionEstimateHistory.pension_account_id == pension_account_id)
            .order_by(PensionEstimateHistory.effective_date)
        )
        return list(result.scalars().all())

    async def get_estimate_history_for_pensions(
        self, pension_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[PensionEstimateHistory]]:
        """Estimate snapshots for many pensions, each list oldest first."""
        if not pension_ids:
            return {}
        result = await self.session.execute(
            select(PensionEstimateHistory)
            .where(PensionEstimateHistory.pension_account_id.in_(pension_ids))
            .order_by(PensionEstimateHistory.effective_date)
        )
        out: dict[uuid.UUID, list[PensionEstimateHistory]] = defaultdict(list)
        for row in result.scalars().all():
            out[row.pension_account_id].append(row)
        return out

    async def get_estimate_on(
        self, pension_account_id: uuid.UUID, effective_date: date
    ) -> PensionEstimateHistory | None:
        result = await self.session.execute(
            select(PensionEstimateHistory).where(
                PensionEstimateHistory.pension_account_id == pension_account_id,
                PensionEstimateHistory.effective_date == effective_date,
            )
        )
        return result.scalar_one_or_none()

    async def get_vested_by_household(
        self, ctx: VisibilityContext
    ) -> list[tuple[PensionAccount, HouseholdMember | None]]:
        visible_accounts = await self._account_repo.get_visible(ctx)
        account_ids = [a.id for a in visible_accounts]
        if not account_ids:
            return []
        result = await self.session.execute(
            select(PensionAccount, HouseholdMember)
            .outerjoin(HouseholdMember, PensionAccount.member_id == HouseholdMember.id)
            .where(
                PensionAccount.account_id.in_(account_ids),
                PensionAccount.is_vested.is_(True),
            )
        )
        return [(row[0], row[1]) for row in result.all()]
