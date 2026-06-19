from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.pension import PensionRepository
from app.schemas.fire import IncomeStream, IncomeStreamType

_PORTFOLIO_ACCOUNT_TYPES = frozenset(
    {
        "investment_brokerage",
        "retirement_401k",
        "retirement_403b",
        "retirement_ira",
        "retirement_roth_ira",
        "pension",
        "hsa",
    }
)

_ASSET_TYPES = frozenset(
    {
        "checking",
        "savings",
        "investment_brokerage",
        "retirement_401k",
        "retirement_403b",
        "retirement_ira",
        "retirement_roth_ira",
        "pension",
        "hsa",
        "real_estate",
        "other_asset",
    }
)

_LIABILITY_TYPES = frozenset(
    {
        "credit_card",
        "mortgage",
        "auto_loan",
        "personal_loan",
        "student_loan",
        "other_liability",
    }
)


def _map_category_to_stream_type(name: str) -> IncomeStreamType:
    """Heuristic: map a category name to the closest IncomeStreamType."""
    lower = name.lower()
    if "salary" in lower or "wage" in lower or "payroll" in lower or "employment" in lower:
        return IncomeStreamType.salary
    if "rent" in lower or "rental" in lower or "lease" in lower:
        return IncomeStreamType.rental
    if "consult" in lower or "freelance" in lower or "contract" in lower:
        return IncomeStreamType.consulting
    if "pension" in lower:
        return IncomeStreamType.pension
    if "social security" in lower or "ssa" in lower or "ssdi" in lower:
        return IncomeStreamType.social_security
    if (
        "dividend" in lower
        or "interest" in lower
        or "investment" in lower
        or "capital gain" in lower
    ):
        return IncomeStreamType.investment
    return IncomeStreamType.other


class FireDetectionResult(BaseModel):
    income_streams: list[IncomeStream]
    gross_income_annual: Decimal
    total_expenses_annual: Decimal
    savings_rate: Decimal
    current_portfolio_value: Decimal
    current_net_worth: Decimal
    detected_at: datetime
    trailing_months_used: int
    months_with_data: int
    warnings: list[str]


class FireInputDetector:
    PORTFOLIO_ACCOUNT_TYPES = _PORTFOLIO_ACCOUNT_TYPES

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.pension_repo = PensionRepository(session)

    async def _sum_by_category(
        self,
        ctx: VisibilityContext,
        is_income: bool,
        since: date,
    ) -> list[tuple[UUID, str, str, Decimal]]:
        """Sum transaction amounts grouped by category for visible accounts."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return []

        result = await self.session.execute(
            select(
                Category.id,
                Category.name,
                Category.is_income,
                func.sum(Transaction.amount).label("total"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_date >= since,
                Transaction.is_transfer.is_(False),
                Category.is_income.is_(is_income),
            )
            .group_by(Category.id, Category.name, Category.is_income)
        )
        rows = result.all()
        return [
            (row.id, row.name, "income" if row.is_income else "expense", Decimal(str(row.total)))
            for row in rows
        ]

    async def _sum_expenses(self, ctx: VisibilityContext, since: date) -> Decimal:
        """Sum absolute value of all non-income, non-transfer transactions."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return Decimal(0)

        result = await self.session.execute(
            select(func.sum(Transaction.amount))
            .join(Category, Category.id == Transaction.category_id, isouter=True)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_date >= since,
                Transaction.is_transfer.is_(False),
                (Category.is_income.is_(False)) | (Transaction.category_id.is_(None)),
            )
        )
        total = result.scalar_one_or_none()
        if total is None:
            return Decimal(0)
        return abs(Decimal(str(total)))

    async def _count_months_with_data(self, ctx: VisibilityContext, since: date) -> int:
        """Count distinct (year, month) pairs with any transactions."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return 0

        result = await self.session.execute(
            select(
                func.count(
                    func.distinct(
                        func.concat(
                            func.extract("year", Transaction.transaction_date),
                            "-",
                            func.extract("month", Transaction.transaction_date),
                        )
                    )
                )
            ).where(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_date >= since,
            )
        )
        count = result.scalar_one_or_none()
        return int(count) if count else 0

    async def _current_portfolio(self, ctx: VisibilityContext) -> Decimal:
        """Get the latest snapshot balance sum for all portfolio accounts."""
        accounts = await self.account_repo.get_visible(ctx)
        portfolio_account_ids = [
            a.id for a in accounts if a.account_type in _PORTFOLIO_ACCOUNT_TYPES
        ]
        if not portfolio_account_ids:
            return Decimal(0)

        latest_date_subq = (
            select(
                AccountSnapshot.account_id,
                func.max(AccountSnapshot.snapshot_date).label("max_date"),
            )
            .where(AccountSnapshot.account_id.in_(portfolio_account_ids))
            .group_by(AccountSnapshot.account_id)
            .subquery()
        )

        result = await self.session.execute(
            select(func.sum(AccountSnapshot.balance)).join(
                latest_date_subq,
                (AccountSnapshot.account_id == latest_date_subq.c.account_id)
                & (AccountSnapshot.snapshot_date == latest_date_subq.c.max_date),
            )
        )
        total = result.scalar_one_or_none()
        return Decimal(str(total)) if total is not None else Decimal(0)

    async def _net_worth(self, ctx: VisibilityContext) -> Decimal:
        """Compute current net worth from latest account snapshots."""
        accounts = await self.account_repo.get_visible(ctx)
        account_ids = [a.id for a in accounts if a.include_in_net_worth]
        if not account_ids:
            return Decimal(0)

        latest_date_subq = (
            select(
                AccountSnapshot.account_id,
                func.max(AccountSnapshot.snapshot_date).label("max_date"),
            )
            .where(AccountSnapshot.account_id.in_(account_ids))
            .group_by(AccountSnapshot.account_id)
            .subquery()
        )

        result = await self.session.execute(
            select(Account.account_type, func.sum(AccountSnapshot.balance))
            .join(
                latest_date_subq,
                (AccountSnapshot.account_id == latest_date_subq.c.account_id)
                & (AccountSnapshot.snapshot_date == latest_date_subq.c.max_date),
            )
            .join(Account, Account.id == AccountSnapshot.account_id)
            .where(AccountSnapshot.account_id.in_(account_ids))
            .group_by(Account.account_type)
        )

        net_worth = Decimal(0)
        for account_type, total in result.all():
            if total is None:
                continue
            val = Decimal(str(total))
            if account_type in _ASSET_TYPES:
                net_worth += val
            elif account_type in _LIABILITY_TYPES:
                net_worth -= val
        return net_worth

    async def _detect_pension_streams(
        self, ctx: VisibilityContext, now: datetime
    ) -> list[IncomeStream]:
        """Build auto-detected income streams for each vested pension account."""
        vested = await self.pension_repo.get_vested_by_household(ctx)
        streams: list[IncomeStream] = []
        current_year = date.today().year
        for pension, member in vested:
            if pension.monthly_benefit_estimate is None:
                continue
            annual = (pension.monthly_benefit_estimate * Decimal(12)).quantize(Decimal("0.01"))
            label_parts = []
            if member is not None and member.display_name:
                label_parts.append(member.display_name)
            label_parts.append("Pension")
            label = " ".join(label_parts)
            start_year = (
                pension.eligibility_date.year
                if pension.eligibility_date is not None
                else (
                    current_year + max(0, (pension.eligibility_age or 65) - 65)
                    if pension.eligibility_age is not None
                    else current_year
                )
            )
            streams.append(
                IncomeStream(
                    id=str(uuid4()),
                    label=label,
                    type=IncomeStreamType.pension,
                    amount_annual=annual,
                    growth_rate_annual=pension.cola_adjustment_rate,
                    start_year=start_year,
                    end_year=None,
                    is_pre_retirement=False,
                    source_account_id=pension.account_id,
                    auto_detected=True,
                    detected_at=now,
                )
            )
        return streams

    async def detect(
        self,
        ctx: VisibilityContext,
        trailing_months: int = 12,
    ) -> FireDetectionResult:
        cutoff = date.today() - relativedelta(months=trailing_months)

        income_by_category = await self._sum_by_category(ctx, is_income=True, since=cutoff)
        total_expenses = await self._sum_expenses(ctx, since=cutoff)
        months_with_data = await self._count_months_with_data(ctx, since=cutoff)

        scale = Decimal(12) / Decimal(max(months_with_data, 1))

        income_streams: list[IncomeStream] = []
        gross_income_annual = Decimal(0)
        now = datetime.now(UTC)
        for _cat_id, cat_name, _cat_type, amount in income_by_category:
            annual = amount * scale
            gross_income_annual += annual
            income_streams.append(
                IncomeStream(
                    id=str(uuid4()),
                    label=cat_name,
                    type=_map_category_to_stream_type(cat_name),
                    amount_annual=annual.quantize(Decimal("0.01")),
                    growth_rate_annual=Decimal("0.03"),
                    start_year=date.today().year,
                    end_year=None,
                    is_pre_retirement=True,
                    auto_detected=True,
                    detected_at=now,
                )
            )

        pension_streams = await self._detect_pension_streams(ctx, now)
        income_streams.extend(pension_streams)

        portfolio_value = await self._current_portfolio(ctx)
        expenses_annual = total_expenses * scale
        savings_rate = (
            (gross_income_annual - expenses_annual) / gross_income_annual
            if gross_income_annual > 0
            else Decimal(0)
        )

        warnings: list[str] = []
        if months_with_data < 6:
            warnings.append(
                f"Only {months_with_data} months of transaction data available. "
                "Detected values may not reflect your typical financial picture."
            )

        return FireDetectionResult(
            income_streams=income_streams,
            gross_income_annual=gross_income_annual,
            total_expenses_annual=expenses_annual,
            savings_rate=savings_rate,
            current_portfolio_value=portfolio_value,
            current_net_worth=await self._net_worth(ctx),
            detected_at=now,
            trailing_months_used=trailing_months,
            months_with_data=months_with_data,
            warnings=warnings,
        )
