import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditRepository, _snapshot, audit
from app.core.visibility import VisibilityContext
from app.db.models.budget import Budget
from app.repositories.budget import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.budget_repo = BudgetRepository(session)
        self.audit_repo = AuditRepository(session)

    async def list_budgets(
        self,
        ctx: VisibilityContext,
        *,
        category_id: uuid.UUID | None = None,
        effective_date: date | None = None,
    ) -> list[Budget]:
        return await self.budget_repo.list_for_household(
            ctx.household_id, category_id=category_id, effective_date=effective_date
        )

    async def _get_or_404(self, ctx: VisibilityContext, budget_id: uuid.UUID) -> Budget:
        budget = await self.budget_repo.get_by_id(ctx.household_id, budget_id)
        if budget is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
        return budget

    @audit("budget.created", "budget")
    async def create(self, ctx: VisibilityContext, data: BudgetCreate) -> Budget:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        conflict = await self.budget_repo.get_by_natural_key(
            ctx.household_id, data.category_id, data.effective_from
        )
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A budget for this category and start date already exists.",
            )
        budget = Budget(
            household_id=ctx.household_id,
            category_id=data.category_id,
            period=data.period,
            amount=data.amount,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
        )
        self.session.add(budget)
        await self.session.flush()
        await self.session.refresh(budget)
        return budget

    @audit("budget.updated", "budget")
    async def update(
        self, ctx: VisibilityContext, budget_id: uuid.UUID, data: BudgetUpdate
    ) -> Budget:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        budget = await self._get_or_404(ctx, budget_id)
        if data.effective_from is not None and data.effective_from != budget.effective_from:
            conflict = await self.budget_repo.get_by_natural_key(
                ctx.household_id, budget.category_id, data.effective_from
            )
            if conflict is not None and conflict.id != budget.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A budget for this category and start date already exists.",
                )
        self._prev_snapshot = _snapshot(budget)

        if data.period is not None:
            budget.period = data.period
        if data.amount is not None:
            budget.amount = data.amount
        if data.effective_from is not None:
            budget.effective_from = data.effective_from
        if "effective_to" in data.model_fields_set:
            budget.effective_to = data.effective_to

        await self.session.flush()
        await self.session.refresh(budget)
        return budget

    async def delete(self, ctx: VisibilityContext, budget_id: uuid.UUID) -> None:
        if not ctx.can_write:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        budget = await self._get_or_404(ctx, budget_id)
        prev = _snapshot(budget)
        await self.session.delete(budget)
        await self.session.flush()

        await self.audit_repo.write(
            ctx=ctx,
            action="budget.deleted",
            entity_type="budget",
            entity_id=budget_id,
            previous_value=prev,
        )
