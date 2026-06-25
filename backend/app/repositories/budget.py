import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.budget import Budget


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_household(
        self,
        household_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        effective_date: date | None = None,
    ) -> list[Budget]:
        q = select(Budget).where(Budget.household_id == household_id)
        if category_id is not None:
            q = q.where(Budget.category_id == category_id)
        if effective_date is not None:
            q = q.where(
                Budget.effective_from <= effective_date,
                or_(Budget.effective_to.is_(None), Budget.effective_to >= effective_date),
            )
        q = q.order_by(Budget.effective_from.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_by_natural_key(
        self, household_id: uuid.UUID, category_id: uuid.UUID, effective_from: date
    ) -> Budget | None:
        """Return the budget matching the unique (household, category, start date)."""
        result = await self.session.execute(
            select(Budget).where(
                Budget.household_id == household_id,
                Budget.category_id == category_id,
                Budget.effective_from == effective_from,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, household_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        result = await self.session.execute(
            select(Budget).where(Budget.id == budget_id, Budget.household_id == household_id)
        )
        return result.scalar_one_or_none()

    async def most_recent_effective(
        self, household_id: uuid.UUID, category_id: uuid.UUID, period_start: date, period_end: date
    ) -> Budget | None:
        result = await self.session.execute(
            select(Budget)
            .where(
                Budget.household_id == household_id,
                Budget.category_id == category_id,
                Budget.effective_from <= period_start,
                or_(Budget.effective_to.is_(None), Budget.effective_to >= period_end),
            )
            .order_by(Budget.effective_from.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_active_for_period(
        self, household_id: uuid.UUID, period_start: date, period_end: date
    ) -> list[Budget]:
        result = await self.session.execute(
            select(Budget)
            .where(
                Budget.household_id == household_id,
                Budget.effective_from <= period_start,
                or_(Budget.effective_to.is_(None), Budget.effective_to >= period_end),
            )
            .order_by(Budget.effective_from.desc(), Budget.id.desc())
        )
        return list(result.scalars().all())
