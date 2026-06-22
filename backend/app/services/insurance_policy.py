from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.insurance_policy import InsurancePolicy


class InsurancePolicyService:
    """Read access to a household's insurance policies (umbrella, life, DI, LTC,
    scheduled/specialty). Household-scoped, no encrypted fields.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_policies(self, ctx: VisibilityContext) -> list[InsurancePolicy]:
        result = await self.session.execute(
            select(InsurancePolicy)
            .where(InsurancePolicy.household_id == ctx.household_id)
            .order_by(InsurancePolicy.created_at)
        )
        return list(result.scalars().all())
