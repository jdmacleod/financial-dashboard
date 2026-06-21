import calendar
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.budget import BudgetRepository
from app.repositories.pension import PensionRepository
from app.repositories.real_estate import RealEstateRepository
from app.schemas.report import (
    BudgetVsActualsItem,
    BudgetVsActualsReport,
    CashFlowPeriod,
    CashFlowReport,
    CashFlowTotals,
    DashboardAccountsSummary,
    DashboardBudgetAlert,
    DashboardCashFlow,
    DashboardNetWorth,
    DashboardResponse,
    DashboardSpendingCategory,
    NetWorthBreakdown,
    NetWorthPoint,
    NetWorthReport,
    PensionAnnotation,
    PropertyExpenseItem,
    PropertyMonthlyPoint,
    PropertyPnLPeriod,
    PropertyPnLReport,
    SpendingByCategoryReport,
    SpendingCategoryItem,
)

Interval = Literal["monthly", "quarterly", "annual"]

PENSION_DISCOUNT_RATE = Decimal("0.04")

ASSET_BUCKET = {
    "checking": "checking_savings",
    "savings": "checking_savings",
    "investment_brokerage": "investment",
    "retirement_401k": "retirement",
    "retirement_403b": "retirement",
    "retirement_ira": "retirement",
    "retirement_roth_ira": "retirement",
    "pension": "retirement",
    "hsa": "hsa",
    "real_estate": "real_estate",
    "other_asset": "other_assets",
}
LIABILITY_BUCKET = {
    "mortgage": "mortgage",
    "credit_card": "other_liabilities",
    "auto_loan": "other_liabilities",
    "personal_loan": "other_liabilities",
    "student_loan": "other_liabilities",
    "other_liability": "other_liabilities",
    "heloc": "other_liabilities",
}
ASSET_TYPES = frozenset(ASSET_BUCKET)
LIABILITY_TYPES = frozenset(LIABILITY_BUCKET)
BREAKDOWN_KEYS = (
    "checking_savings",
    "investment",
    "retirement",
    "real_estate",
    "hsa",
    "other_assets",
    "mortgage",
    "other_liabilities",
)


def _month_ends(from_date: date, to_date: date) -> list[date]:
    if from_date > to_date:
        return []
    result: list[date] = []
    y, m = from_date.year, from_date.month
    while date(y, m, 1) <= to_date:
        result.append(date(y, m, calendar.monthrange(y, m)[1]))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return result


def _period_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)
        self.budget_repo = BudgetRepository(session)
        self.property_repo = RealEstateRepository(session)
        self.pension_repo = PensionRepository(session)

    async def _visible_accounts(self, ctx: VisibilityContext) -> list[Account]:
        return await self.account_repo.get_visible(ctx, is_active=True)

    async def _category_map(self, ctx: VisibilityContext) -> dict[uuid.UUID, Category]:
        result = await self.session.execute(
            select(Category).where(Category.household_id == ctx.household_id)
        )
        return {c.id: c for c in result.scalars().all()}

    # --- Net worth -----------------------------------------------------

    async def _snapshot_balance_at(self, account_id: uuid.UUID, as_of: date) -> Decimal | None:
        result = await self.session.execute(
            select(AccountSnapshot.balance)
            .where(AccountSnapshot.account_id == account_id, AccountSnapshot.snapshot_date <= as_of)
            .order_by(AccountSnapshot.snapshot_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _running_txn_balance_at(self, account_id: uuid.UUID, as_of: date) -> Decimal:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.account_id == account_id, Transaction.transaction_date <= as_of
            )
        )
        return Decimal(result.scalar_one())

    async def _debt_balance(self, account_id: uuid.UUID) -> Decimal | None:
        result = await self.session.execute(
            select(Debt.current_balance).where(Debt.account_id == account_id)
        )
        return result.scalar_one_or_none()

    async def _property_value_at(self, account_id: uuid.UUID, as_of: date) -> Decimal:
        prop = await self.property_repo.get_by_account_id(account_id)
        if prop is None:
            return Decimal("0")
        valuation = await self.property_repo.latest_valuation_as_of(prop.id, as_of)
        return valuation.estimated_value if valuation is not None else Decimal("0")

    async def _asset_value_at(
        self,
        account: Account,
        as_of: date,
        property_values: dict[uuid.UUID, Decimal] | None = None,
        pension_values: dict[uuid.UUID, Decimal] | None = None,
    ) -> Decimal:
        snap = await self._snapshot_balance_at(account.id, as_of)
        if snap is not None:
            return snap
        if account.account_type in ("checking", "savings"):
            return await self._running_txn_balance_at(account.id, as_of)
        if account.account_type == "real_estate":
            if property_values is not None:
                return property_values.get(account.id, Decimal("0"))
            return await self._property_value_at(account.id, as_of)
        if account.account_type == "pension":
            if pension_values is not None:
                return pension_values.get(account.id, Decimal("0"))
            pension = await self.pension_repo.get_by_account_id(account.id)
            if pension and pension.monthly_benefit_estimate:
                return pension.monthly_benefit_estimate * 12 / PENSION_DISCOUNT_RATE
            return Decimal("0")
        return Decimal("0")

    async def _liability_value_at(
        self,
        account: Account,
        as_of: date,
        txn_sums: dict[uuid.UUID, Decimal] | None = None,
    ) -> Decimal:
        if account.account_type in ("credit_card", "heloc"):
            # Transaction-based liabilities: balance comes from running transaction sum.
            if txn_sums is not None:
                return abs(txn_sums.get(account.id, Decimal("0")))
            txn = await self._running_txn_balance_at(account.id, as_of)
            return abs(txn)
        debt_balance = await self._debt_balance(account.id)
        if debt_balance is not None:
            return abs(debt_balance)
        snap = await self._snapshot_balance_at(account.id, as_of)
        return abs(snap) if snap is not None else Decimal("0")

    async def _net_worth_point(
        self,
        accounts: list[Account],
        as_of: date,
        property_values: dict[uuid.UUID, Decimal] | None = None,
        pension_values: dict[uuid.UUID, Decimal] | None = None,
        txn_sums: dict[uuid.UUID, Decimal] | None = None,
    ) -> NetWorthPoint:
        breakdown = {key: Decimal("0") for key in BREAKDOWN_KEYS}
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        for account in accounts:
            if account.account_type in ASSET_TYPES:
                value = await self._asset_value_at(account, as_of, property_values, pension_values)
                breakdown[ASSET_BUCKET[account.account_type]] += value
                total_assets += value
            elif account.account_type in LIABILITY_TYPES:
                value = await self._liability_value_at(account, as_of, txn_sums)
                breakdown[LIABILITY_BUCKET[account.account_type]] -= value
                total_liabilities += value
        return NetWorthPoint(
            date=as_of,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            net_worth=total_assets - total_liabilities,
            breakdown=NetWorthBreakdown(**breakdown),
        )

    async def current_net_worth(self, ctx: VisibilityContext, as_of: date) -> NetWorthPoint:
        accounts = [a for a in await self._visible_accounts(ctx) if a.include_in_net_worth]
        pension_account_ids = [a.id for a in accounts if a.account_type == "pension"]
        pensions = (
            await self.pension_repo.get_by_account_ids(pension_account_ids)
            if pension_account_ids
            else []
        )
        pension_values = {
            p.account_id: p.monthly_benefit_estimate * 12 / PENSION_DISCOUNT_RATE
            for p in pensions
            if p.monthly_benefit_estimate
        }
        return await self._net_worth_point(accounts, as_of, pension_values=pension_values)

    async def net_worth(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
        interval: Interval = "monthly",
    ) -> NetWorthReport:
        accounts = [a for a in await self._visible_accounts(ctx) if a.include_in_net_worth]
        month_ends = _month_ends(from_date, to_date)
        if interval == "quarterly":
            month_ends = [d for d in month_ends if d.month in (3, 6, 9, 12)]
        elif interval == "annual":
            month_ends = [d for d in month_ends if d.month == 12]
        if not month_ends:
            month_ends = [to_date]

        # Pre-load real_estate properties once; then batch-fetch valuations per
        # date point (1 query/point instead of 2xN queries/point for N properties).
        re_account_ids = [a.id for a in accounts if a.account_type == "real_estate"]
        props = await self.property_repo.list_for_accounts(re_account_ids) if re_account_ids else []
        account_to_prop_id = {p.account_id: p.id for p in props}

        # Pre-fetch pension PV once — PensionAccount data is static (no per-date history).
        # Avoids NxM queries (N pensions x M date points) for data that doesn't change.
        pension_account_ids = [a.id for a in accounts if a.account_type == "pension"]
        pensions = (
            await self.pension_repo.get_by_account_ids(pension_account_ids)
            if pension_account_ids
            else []
        )
        pension_values = {
            p.account_id: p.monthly_benefit_estimate * 12 / PENSION_DISCOUNT_RATE
            for p in pensions
            if p.monthly_benefit_estimate
        }

        # Pre-identify transaction-based liability accounts (credit_card, heloc).
        # Sums are batched per date point: 1 query/point instead of N_accounts/point.
        txn_liability_ids = [
            a.id for a in accounts if a.account_type in ("credit_card", "heloc")
        ]

        series = []
        for as_of in month_ends:
            if account_to_prop_id:
                raw = await self.property_repo.batch_latest_valuations_as_of(
                    list(account_to_prop_id.values()), as_of
                )
                property_values = {
                    acc_id: raw.get(prop_id, Decimal("0"))
                    for acc_id, prop_id in account_to_prop_id.items()
                }
            else:
                property_values = {}

            txn_sums: dict[uuid.UUID, Decimal] | None = None
            if txn_liability_ids:
                txn_result = await self.session.execute(
                    select(Transaction.account_id, func.sum(Transaction.amount))
                    .where(
                        Transaction.account_id.in_(txn_liability_ids),
                        Transaction.transaction_date <= as_of,
                    )
                    .group_by(Transaction.account_id)
                )
                txn_sums = {acc_id: Decimal(str(total)) for acc_id, total in txn_result.all()}

            series.append(
                await self._net_worth_point(accounts, as_of, property_values, pension_values, txn_sums)
            )
        pension_annotations = await self._pension_annotations(ctx, accounts)
        return NetWorthReport(
            series=series,
            current=series[-1] if series else None,
            pension_annotations=pension_annotations,
        )

    async def _pension_annotations(
        self, ctx: VisibilityContext, accounts: list[Account]
    ) -> list[PensionAnnotation]:
        pension_account_ids = [a.id for a in accounts if a.account_type == "pension"]
        if not pension_account_ids:
            return []
        pensions = await self.pension_repo.get_by_account_ids(pension_account_ids)
        account_map = {a.id: a for a in accounts}
        return [
            PensionAnnotation(
                account_id=p.account_id,
                nickname=account_map[p.account_id].nickname,
                monthly_benefit=p.monthly_benefit_estimate,
                eligibility_age=p.eligibility_age,
                eligibility_date=p.eligibility_date,
            )
            for p in pensions
            if p.account_id in account_map
        ]

    # --- Cash flow -------------------------------------------------------

    async def cash_flow(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
        group_by: Literal["month", "quarter"] = "month",
    ) -> CashFlowReport:
        accounts = await self._visible_accounts(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            zero = CashFlowTotals(
                income=Decimal("0"), expenses=Decimal("0"), net=Decimal("0"), savings_rate=0.0
            )
            return CashFlowReport(series=[], totals=zero)

        cat_map = await self._category_map(ctx)
        result = await self.session.execute(
            select(Transaction.transaction_date, Transaction.amount, Transaction.category_id).where(
                Transaction.account_id.in_(account_ids),
                Transaction.is_transfer.is_(False),
                Transaction.transaction_date >= from_date,
                Transaction.transaction_date <= to_date,
            )
        )

        periods: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"income": Decimal("0"), "expenses": Decimal("0")}
        )
        for txn_date, amount, category_id in result.all():
            category = cat_map.get(category_id)
            is_income = category.is_income if category else False
            if group_by == "quarter":
                key = f"{txn_date.year:04d}-Q{(txn_date.month - 1) // 3 + 1}"
            else:
                key = _period_key(txn_date)
            if is_income:
                periods[key]["income"] += amount
            elif amount < 0:
                periods[key]["expenses"] += -amount

        series = []
        for key in sorted(periods):
            income = periods[key]["income"]
            expenses = periods[key]["expenses"]
            net = income - expenses
            savings_rate = float(net / income) if income > 0 else 0.0
            series.append(
                CashFlowPeriod(
                    period=key, income=income, expenses=expenses, net=net, savings_rate=savings_rate
                )
            )

        total_income = sum((p.income for p in series), Decimal("0"))
        total_expenses = sum((p.expenses for p in series), Decimal("0"))
        total_net = total_income - total_expenses
        total_savings_rate = float(total_net / total_income) if total_income > 0 else 0.0
        totals = CashFlowTotals(
            income=total_income,
            expenses=total_expenses,
            net=total_net,
            savings_rate=total_savings_rate,
        )
        return CashFlowReport(series=series, totals=totals)

    # --- Spending by category --------------------------------------------

    async def spending_by_category(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
        parent_category_id: uuid.UUID | None = None,
    ) -> SpendingByCategoryReport:
        accounts = await self._visible_accounts(ctx)
        account_ids = [a.id for a in accounts]
        cat_map = await self._category_map(ctx)
        if not account_ids:
            return SpendingByCategoryReport(total=Decimal("0"), categories=[])

        child_counts: dict[uuid.UUID, int] = defaultdict(int)
        for c in cat_map.values():
            if c.parent_category_id:
                child_counts[c.parent_category_id] += 1

        include_uncategorized = parent_category_id is None
        if parent_category_id is not None:
            target_categories = [
                c for c in cat_map.values() if c.parent_category_id == parent_category_id
            ]
        else:
            target_categories = [
                c for c in cat_map.values() if c.parent_category_id is None and not c.is_income
            ]

        result = await self.session.execute(
            select(Transaction.category_id, func.sum(Transaction.amount), func.count())
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.is_transfer.is_(False),
                Transaction.amount < 0,
                Transaction.transaction_date >= from_date,
                Transaction.transaction_date <= to_date,
            )
            .group_by(Transaction.category_id)
        )
        sums: dict[uuid.UUID | None, tuple[Decimal, int]] = {
            cat_id: (abs(total), count) for cat_id, total, count in result.all()
        }

        items = []
        for c in target_categories:
            amount, count = sums.get(c.id, (Decimal("0"), 0))
            items.append(
                SpendingCategoryItem(
                    category_id=c.id,
                    name=c.name,
                    amount=amount,
                    percentage=0.0,
                    transaction_count=count,
                    has_children=child_counts.get(c.id, 0) > 0,
                )
            )
        if include_uncategorized:
            amount, count = sums.get(None, (Decimal("0"), 0))
            if count > 0:
                items.append(
                    SpendingCategoryItem(
                        category_id=None,
                        name="Uncategorized",
                        amount=amount,
                        percentage=0.0,
                        transaction_count=count,
                        has_children=False,
                    )
                )

        total = sum((i.amount for i in items), Decimal("0"))
        for item in items:
            item.percentage = float(item.amount / total * 100) if total > 0 else 0.0
        items.sort(key=lambda i: i.amount, reverse=True)
        return SpendingByCategoryReport(total=total, categories=items)

    # --- Budget vs actuals -------------------------------------------------

    async def budget_vs_actuals(self, ctx: VisibilityContext, month: str) -> BudgetVsActualsReport:
        year, mo = (int(p) for p in month.split("-"))
        period_start = date(year, mo, 1)
        period_end = date(year, mo, calendar.monthrange(year, mo)[1])

        budgets = await self.budget_repo.list_active_for_period(
            ctx.household_id, period_start, period_end
        )
        best: dict[uuid.UUID, BudgetVsActualsItem] = {}
        latest_effective: dict[uuid.UUID, date] = {}
        for b in budgets:
            if (
                b.category_id not in latest_effective
                or b.effective_from > latest_effective[b.category_id]
            ):
                latest_effective[b.category_id] = b.effective_from

        chosen = {
            b.category_id: b
            for b in budgets
            if b.effective_from == latest_effective.get(b.category_id)
        }

        accounts = await self._visible_accounts(ctx)
        account_ids = [a.id for a in accounts]
        cat_map = await self._category_map(ctx)

        actuals: dict[uuid.UUID, Decimal] = {}
        if account_ids and chosen:
            result = await self.session.execute(
                select(Transaction.category_id, func.sum(Transaction.amount))
                .where(
                    Transaction.account_id.in_(account_ids),
                    Transaction.is_transfer.is_(False),
                    Transaction.amount < 0,
                    Transaction.category_id.in_(list(chosen.keys())),
                    Transaction.transaction_date >= period_start,
                    Transaction.transaction_date <= period_end,
                )
                .group_by(Transaction.category_id)
            )
            actuals = {cat_id: abs(total) for cat_id, total in result.all()}

        for category_id, budget in chosen.items():
            category = cat_map.get(category_id)
            actual = actuals.get(category_id, Decimal("0"))
            remaining = budget.amount - actual
            pct = float(actual / budget.amount * 100) if budget.amount > 0 else 0.0
            best[category_id] = BudgetVsActualsItem(
                category_id=category_id,
                name=category.name if category else "Unknown",
                budget=budget.amount,
                actual=actual,
                remaining=remaining,
                percentage_used=pct,
            )

        items = sorted(best.values(), key=lambda i: i.percentage_used, reverse=True)
        return BudgetVsActualsReport(period=month, categories=items)

    # --- Property P&L -------------------------------------------------

    async def property_pnl(
        self, ctx: VisibilityContext, property_id: uuid.UUID, from_date: date, to_date: date
    ) -> PropertyPnLReport:
        property_ = await self.property_repo.get_by_id(property_id)
        if property_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
        account = await self.account_repo.get_by_id(ctx, property_.account_id)
        cat_map = await self._category_map(ctx)

        result = await self.session.execute(
            select(Transaction.transaction_date, Transaction.amount, Transaction.category_id).where(
                Transaction.real_estate_property_id == property_id,
                Transaction.is_transfer.is_(False),
                Transaction.transaction_date >= from_date,
                Transaction.transaction_date <= to_date,
            )
        )

        gross_income = Decimal("0")
        total_expenses = Decimal("0")
        expense_by_category: dict[uuid.UUID | None, Decimal] = defaultdict(lambda: Decimal("0"))
        monthly: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"income": Decimal("0"), "expenses": Decimal("0")}
        )

        for txn_date, amount, category_id in result.all():
            category = cat_map.get(category_id)
            is_income = category.is_income if category else False
            key = _period_key(txn_date)
            if is_income:
                gross_income += amount
                monthly[key]["income"] += amount
            else:
                total_expenses += abs(amount)
                expense_by_category[category_id] += abs(amount)
                monthly[key]["expenses"] += abs(amount)

        net_income = gross_income - total_expenses

        latest_valuation = await self.property_repo.latest_valuation(property_id)
        net_yield_pct = None
        if latest_valuation and latest_valuation.estimated_value > 0:
            net_yield_pct = float(net_income / latest_valuation.estimated_value * 100)

        expense_breakdown = [
            PropertyExpenseItem(
                category_id=cid,
                name=cat_map[cid].name if cid is not None and cid in cat_map else "Uncategorized",
                amount=amt,
            )
            for cid, amt in sorted(expense_by_category.items(), key=lambda kv: kv[1], reverse=True)
        ]
        monthly_series = [
            PropertyMonthlyPoint(
                period=p,
                income=v["income"],
                expenses=v["expenses"],
                net=v["income"] - v["expenses"],
            )
            for p, v in sorted(monthly.items())
        ]

        return PropertyPnLReport(
            property_id=property_id,
            nickname=account.nickname,
            address=decrypt(property_.address_enc),
            period=PropertyPnLPeriod.model_validate({"from": from_date, "to": to_date}),
            gross_income=gross_income,
            total_expenses=total_expenses,
            net_income=net_income,
            net_yield_pct=net_yield_pct,
            expense_breakdown=expense_breakdown,
            monthly_series=monthly_series,
        )

    # --- Dashboard -------------------------------------------------------

    async def dashboard(self, ctx: VisibilityContext) -> DashboardResponse:
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        month_start = today.replace(day=1)

        current_point = await self.current_net_worth(ctx, today)
        prior_point = await self.current_net_worth(ctx, thirty_days_ago)
        change_30d = current_point.net_worth - prior_point.net_worth
        change_30d_pct = (
            float(change_30d / abs(prior_point.net_worth) * 100)
            if prior_point.net_worth != 0
            else None
        )

        cash_flow_report = await self.cash_flow(ctx, month_start, today)
        spending_report = await self.spending_by_category(ctx, month_start, today)
        top_categories = spending_report.categories[:5]

        bva = await self.budget_vs_actuals(ctx, today.strftime("%Y-%m"))
        budget_alerts = [
            DashboardBudgetAlert(category=item.name, used_pct=item.percentage_used)
            for item in bva.categories
            if item.percentage_used > 90
        ]

        return DashboardResponse(
            net_worth=DashboardNetWorth(
                current=current_point.net_worth,
                change_30d=change_30d,
                change_30d_pct=change_30d_pct,
            ),
            cash_flow_mtd=DashboardCashFlow(
                income=cash_flow_report.totals.income,
                expenses=cash_flow_report.totals.expenses,
                net=cash_flow_report.totals.net,
            ),
            top_spending_categories=[
                DashboardSpendingCategory(category_id=c.category_id, name=c.name, amount=c.amount)
                for c in top_categories
            ],
            budget_alerts=budget_alerts,
            accounts_summary=DashboardAccountsSummary(
                total_assets=current_point.total_assets,
                total_liabilities=current_point.total_liabilities,
            ),
        )
