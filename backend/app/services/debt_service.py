from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.debt import Debt
from app.repositories.account import AccountRepository
from app.schemas.fire import (
    DebtPayoffComparisonResponse,
    DebtPayoffMonthResponse,
    DebtPayoffPlanResponse,
    DebtWithAccountResponse,
)
from app.services.debt_projector import DebtPayoffPlan, DebtRecord, project_payoff


def _plan_to_response(plan: DebtPayoffPlan) -> DebtPayoffPlanResponse:
    monthly = [
        DebtPayoffMonthResponse(
            month=m.month,
            date=m.date,
            total_remaining=m.total_remaining,
            per_debt={str(k): v for k, v in m.per_debt.items()},
        )
        for m in plan.monthly_series
    ]
    return DebtPayoffPlanResponse(
        strategy=plan.strategy,
        months_to_payoff=plan.months_to_payoff,
        total_interest_paid=plan.total_interest_paid,
        payoff_date=plan.payoff_date,
        monthly_series=monthly,
        payoff_order=plan.payoff_order,
    )


class DebtService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)

    async def list_with_accounts(self, ctx: VisibilityContext) -> list[DebtWithAccountResponse]:
        """List all debts for visible accounts."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return []

        account_map = {a.id: a for a in accounts}

        result = await self.session.execute(select(Debt).where(Debt.account_id.in_(account_ids)))
        debts = list(result.scalars().all())

        return [
            DebtWithAccountResponse(
                debt_id=d.id,
                account_id=d.account_id,
                nickname=account_map[d.account_id].nickname,
                current_balance=d.current_balance,
                interest_rate=d.interest_rate,
                minimum_payment=d.minimum_payment,
            )
            for d in debts
            if d.account_id in account_map
        ]

    async def get_payoff_comparison(
        self,
        ctx: VisibilityContext,
        extra_monthly_payment: Decimal = Decimal(0),
    ) -> DebtPayoffComparisonResponse:
        """Return both avalanche and snowball plans side by side."""
        debt_responses = await self.list_with_accounts(ctx)

        records = [
            DebtRecord(
                id=dr.debt_id,
                nickname=dr.nickname,
                current_balance=dr.current_balance,
                interest_rate=dr.interest_rate,
                minimum_payment=dr.minimum_payment,
            )
            for dr in debt_responses
        ]

        avalanche_plan = project_payoff(records, extra_monthly_payment, "avalanche")
        snowball_plan = project_payoff(records, extra_monthly_payment, "snowball")

        return DebtPayoffComparisonResponse(
            debts=debt_responses,
            avalanche=_plan_to_response(avalanche_plan),
            snowball=_plan_to_response(snowball_plan),
        )
