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
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionAccount, PensionEstimateHistory
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.repositories.account import AccountRepository
from app.repositories.budget import BudgetRepository
from app.repositories.ownership_entity import OwnershipEntityRepository, counts_in_net_worth
from app.repositories.pension import PensionRepository
from app.repositories.real_estate import RealEstateRepository
from app.schemas.report import (
    BudgetTrendPoint,
    BudgetTrendReport,
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
    EstateExposureEntity,
    EstateExposureReport,
    NetWorthBreakdown,
    NetWorthPoint,
    NetWorthReport,
    PensionAnnotation,
    PropertyExpenseItem,
    PropertyMonthlyPoint,
    PropertyPnLPeriod,
    PropertyPnLReport,
    RetirementIncomeBreakdown,
    SavingsRatePoint,
    SavingsRateReport,
    SpendingByCategoryReport,
    SpendingCategoryItem,
)
from app.services.pension_valuation import pension_present_value, pension_value_at

Interval = Literal["monthly", "quarterly", "annual"]

# A pension plus its estimate history, used to value the account from the
# estimate in effect at each net-worth date.
_PensionData = tuple[PensionAccount | None, list[PensionEstimateHistory]]

# Maps retirement-income category slugs (see seed shared_categories.py) to the
# labeled buckets surfaced in the cash-flow report.
RETIREMENT_INCOME_SLUGS = {
    "social_security_income": "social_security",
    "pension_income": "pension",
    "rmd_distribution": "rmd",
}

# Federal estate-tax parameters. The 2025 OBBBA made the higher unified credit
# permanent and set the per-decedent exemption at $15,000,000 for 2026 (indexed
# thereafter); the top marginal rate is 40%. These are intentionally module
# constants — single-installation, USD-only, no state-tax modelling in v1.
FEDERAL_ESTATE_EXEMPTION_PER_PERSON = Decimal("15000000")
FEDERAL_ESTATE_TAX_RATE = Decimal("0.40")

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
    # Demo-data extension (migration 0007): snapshot-valued asset accounts.
    "inherited_ira": "retirement",
    "treasury": "investment",
    "private_fund": "other_assets",
    "life_insurance_cash_value": "other_assets",
}
LIABILITY_BUCKET = {
    "mortgage": "mortgage",
    "credit_card": "other_liabilities",
    "auto_loan": "other_liabilities",
    "personal_loan": "other_liabilities",
    "student_loan": "other_liabilities",
    "other_liability": "other_liabilities",
    "heloc": "other_liabilities",
    # Demo-data extension (migration 0007): revolving credit lines, valued from
    # the running transaction sum (see TXN_TRACKED_LIABILITY_TYPES).
    "sbloc": "other_liabilities",
    "margin": "other_liabilities",
}
ASSET_TYPES = frozenset(ASSET_BUCKET)
LIABILITY_TYPES = frozenset(LIABILITY_BUCKET)
# Liabilities whose point-in-time balance comes from the running transaction
# sum at each date, so the value amortizes as payments/draws post. Revolving
# credit (credit_card/heloc/sbloc/margin) plus amortizing consumer loans tracked
# by transactions. A static Debt.current_balance would otherwise render a flat
# line across the whole net-worth history and ignore every payment made — so
# attaching a Debt record to any of these must not pin it to a single value.
TXN_TRACKED_LIABILITY_TYPES = frozenset(
    {"credit_card", "heloc", "student_loan", "auto_loan", "personal_loan", "sbloc", "margin"}
)
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
        self.entity_repo = OwnershipEntityRepository(session)

    async def _visible_accounts(self, ctx: VisibilityContext) -> list[Account]:
        return await self.account_repo.get_visible(ctx, is_active=True)

    async def _net_worth_accounts(self, ctx: VisibilityContext) -> list[Account]:
        """Visible accounts that contribute to personal net worth: respects both
        the account's include_in_net_worth flag and any ownership entity's
        counts_in_personal_net_worth flag (ILIT/CRT/DAF-held assets excluded).
        """
        accounts = await self._visible_accounts(ctx)
        entity_map = await self.entity_repo.get_map(ctx.household_id)
        return [a for a in accounts if counts_in_net_worth(a, entity_map)]

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
        pension_data_by_account: dict[uuid.UUID, _PensionData] | None = None,
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
            if pension_data_by_account is not None:
                pension, history = pension_data_by_account.get(account.id, (None, []))
            else:
                pension = await self.pension_repo.get_by_account_id(account.id)
                history = (
                    await self.pension_repo.get_estimate_history(pension.id) if pension else []
                )
            return pension_value_at(pension, history, as_of)
        return Decimal("0")

    async def _liability_value_at(
        self,
        account: Account,
        as_of: date,
        txn_sums: dict[uuid.UUID, Decimal] | None = None,
    ) -> Decimal:
        if account.account_type in TXN_TRACKED_LIABILITY_TYPES:
            # Balance comes from the running transaction sum at `as_of` so it
            # amortizes over time as payments post. Debt.current_balance is a
            # single present-day figure and is used only as a fallback for
            # accounts that carry no transactions to anchor the balance.
            if txn_sums is not None:
                if account.id in txn_sums:
                    return abs(txn_sums[account.id])
                # Absent from the batched sums => no transactions for this account.
            else:
                txn = await self._running_txn_balance_at(account.id, as_of)
                if txn != 0:
                    return abs(txn)
                # A zero running sum may mean "no transactions" rather than
                # "paid off"; fall through to a Debt record when one exists.
            debt_balance = await self._debt_balance(account.id)
            if debt_balance is not None:
                return abs(debt_balance)
            # Last resort: a snapshot (e.g. a line of credit imported as a balance
            # snapshot with no transactions or Debt record).
            snap = await self._snapshot_balance_at(account.id, as_of)
            if snap is not None:
                return abs(snap)
            return Decimal("0")
        # Mortgage / other_liability: a structured Debt record is the source of
        # truth, then a snapshot, then the running transaction sum (e.g. a
        # mortgage imported from CSV with no Debt record).
        debt_balance = await self._debt_balance(account.id)
        if debt_balance is not None:
            return abs(debt_balance)
        snap = await self._snapshot_balance_at(account.id, as_of)
        if snap is not None:
            return abs(snap)
        if txn_sums is not None:
            return abs(txn_sums.get(account.id, Decimal("0")))
        txn = await self._running_txn_balance_at(account.id, as_of)
        return abs(txn)

    async def _net_worth_point(
        self,
        accounts: list[Account],
        as_of: date,
        property_values: dict[uuid.UUID, Decimal] | None = None,
        pension_data_by_account: dict[uuid.UUID, _PensionData] | None = None,
        txn_sums: dict[uuid.UUID, Decimal] | None = None,
    ) -> NetWorthPoint:
        breakdown = {key: Decimal("0") for key in BREAKDOWN_KEYS}
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        for account in accounts:
            if account.account_type in ASSET_TYPES:
                value = await self._asset_value_at(
                    account, as_of, property_values, pension_data_by_account
                )
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

    async def _pension_data_for_accounts(
        self, accounts: list[Account]
    ) -> dict[uuid.UUID, _PensionData]:
        """Map account_id -> (pension, estimate history) for the pension accounts
        in ``accounts``. The history lets each net-worth date be valued from the
        estimate in effect then."""
        pension_account_ids = [a.id for a in accounts if a.account_type == "pension"]
        if not pension_account_ids:
            return {}
        pensions = await self.pension_repo.get_by_account_ids(pension_account_ids)
        hist_map = await self.pension_repo.get_estimate_history_for_pensions(
            [p.id for p in pensions]
        )
        return {p.account_id: (p, hist_map.get(p.id, [])) for p in pensions}

    async def current_net_worth(self, ctx: VisibilityContext, as_of: date) -> NetWorthPoint:
        accounts = await self._net_worth_accounts(ctx)
        pension_data_by_account = await self._pension_data_for_accounts(accounts)
        return await self._net_worth_point(
            accounts, as_of, pension_data_by_account=pension_data_by_account
        )

    async def net_worth(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
        interval: Interval = "monthly",
    ) -> NetWorthReport:
        accounts = await self._net_worth_accounts(ctx)
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

        # Pre-fetch pension records and their estimate history once to avoid NxM
        # queries (N pensions x M date points). The present value is still
        # computed per date point because both a deferred pension's PV and the
        # estimate in effect change over time.
        pension_data_by_account = await self._pension_data_for_accounts(accounts)

        # Batch transaction sums for ALL liability accounts per date point.
        # credit_card/heloc use them directly; mortgage/loan/etc. fall back to them
        # when no Debt record or AccountSnapshot exists.
        txn_liability_ids = [a.id for a in accounts if a.account_type in LIABILITY_TYPES]

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
                await self._net_worth_point(
                    accounts, as_of, property_values, pension_data_by_account, txn_sums
                )
            )
        pension_annotations = await self._pension_annotations(ctx, accounts, to_date)
        return NetWorthReport(
            series=series,
            current=series[-1] if series else None,
            pension_annotations=pension_annotations,
        )

    async def _pension_annotations(
        self, ctx: VisibilityContext, accounts: list[Account], as_of: date
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
                estimated_pv=(
                    pension_present_value(p, as_of) if p.monthly_benefit_estimate else None
                ),
            )
            for p in pensions
            if p.account_id in account_map
        ]

    # --- Estate exposure -------------------------------------------------

    async def _exemption_holders(self, ctx: VisibilityContext) -> int:
        """Number of federal estate-tax exemptions the household can apply: one
        per primary/partner member, capped at two (a married couple shields up
        to 2x the per-person exemption via portability). At least one.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(HouseholdMember)
            .where(
                HouseholdMember.household_id == ctx.household_id,
                HouseholdMember.is_active.is_(True),
                HouseholdMember.role.in_(("primary", "partner")),
            )
        )
        count = int(result.scalar_one())
        return max(1, min(count, 2))

    async def estate_exposure(self, ctx: VisibilityContext, as_of: date) -> EstateExposureReport:
        """Computed federal estate-exposure report.

        Groups every visible active account by its titling (ownership entity, or
        directly-owned), nets assets against liabilities per bucket, and splits
        the total into the taxable estate (directly-owned + revocable-trust) vs.
        holdings removed from the estate (ILIT / irrevocable trust / CRT, where
        ``is_in_taxable_estate`` is False). The gross taxable estate is compared
        against the applicable federal exemption to estimate exposure. Unlike
        net worth, this lens ignores ``include_in_net_worth`` /
        ``counts_in_personal_net_worth`` — estate inclusion follows legal
        titling, not display preference.
        """
        accounts = await self._visible_accounts(ctx)
        entity_map = await self.entity_repo.get_map(ctx.household_id)

        # Pre-compute pension data so pension accounts value identically to the
        # net-worth report.
        pension_data_by_account = await self._pension_data_for_accounts(accounts)

        # Accumulate assets and liabilities per titling bucket. Key is the
        # ownership_entity_id, or None for directly-owned holdings.
        assets: dict[uuid.UUID | None, Decimal] = defaultdict(lambda: Decimal("0"))
        liabilities: dict[uuid.UUID | None, Decimal] = defaultdict(lambda: Decimal("0"))
        for account in accounts:
            bucket = account.ownership_entity_id
            if account.account_type in ASSET_TYPES:
                assets[bucket] += await self._asset_value_at(
                    account, as_of, pension_data_by_account=pension_data_by_account
                )
            elif account.account_type in LIABILITY_TYPES:
                liabilities[bucket] += await self._liability_value_at(account, as_of)

        bucket_ids: set[uuid.UUID | None] = set(assets) | set(liabilities)
        entity_rows: list[EstateExposureEntity] = []
        gross_taxable_estate = Decimal("0")
        excluded_from_estate = Decimal("0")
        for bucket in bucket_ids:
            entity = entity_map.get(bucket) if bucket is not None else None
            in_estate = (
                True if bucket is None else (entity.is_in_taxable_estate if entity else True)
            )
            asset_total = assets.get(bucket, Decimal("0"))
            liability_total = liabilities.get(bucket, Decimal("0"))
            net_value = asset_total - liability_total
            if in_estate:
                gross_taxable_estate += net_value
            else:
                excluded_from_estate += net_value
            entity_rows.append(
                EstateExposureEntity(
                    entity_id=bucket,
                    entity_name=decrypt(entity.name_enc) if entity is not None else None,
                    entity_type=entity.entity_type if entity is not None else None,
                    is_in_taxable_estate=in_estate,
                    assets=asset_total,
                    liabilities=liability_total,
                    net_value=net_value,
                )
            )

        # Directly-owned first, then entity buckets by descending net value.
        entity_rows.sort(key=lambda r: (r.entity_id is not None, -r.net_value))

        holders = await self._exemption_holders(ctx)
        applicable_exemption = FEDERAL_ESTATE_EXEMPTION_PER_PERSON * holders
        taxable_overage = max(Decimal("0"), gross_taxable_estate - applicable_exemption)
        estimated_tax = taxable_overage * FEDERAL_ESTATE_TAX_RATE
        return EstateExposureReport(
            as_of=as_of,
            gross_taxable_estate=gross_taxable_estate,
            excluded_from_estate=excluded_from_estate,
            total_net_worth=gross_taxable_estate + excluded_from_estate,
            exemption_per_person=FEDERAL_ESTATE_EXEMPTION_PER_PERSON,
            exemption_holders=holders,
            applicable_exemption=applicable_exemption,
            taxable_overage=taxable_overage,
            estimated_federal_estate_tax=estimated_tax,
            federal_estate_tax_rate=float(FEDERAL_ESTATE_TAX_RATE),
            entities=entity_rows,
        )

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
            return CashFlowReport(
                series=[],
                totals=zero,
                retirement_income=RetirementIncomeBreakdown(
                    social_security=Decimal("0"),
                    pension=Decimal("0"),
                    rmd=Decimal("0"),
                    total=Decimal("0"),
                    has_data=False,
                ),
            )

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
        retirement = {bucket: Decimal("0") for bucket in RETIREMENT_INCOME_SLUGS.values()}
        for txn_date, amount, category_id in result.all():
            category = cat_map.get(category_id)
            is_income = category.is_income if category else False
            if group_by == "quarter":
                key = f"{txn_date.year:04d}-Q{(txn_date.month - 1) // 3 + 1}"
            else:
                key = _period_key(txn_date)
            if is_income:
                periods[key]["income"] += amount
                bucket = category and category.slug and RETIREMENT_INCOME_SLUGS.get(category.slug)
                if bucket:
                    retirement[bucket] += amount
            elif amount < 0:
                periods[key]["expenses"] += -amount

        series = []
        for key in sorted(periods):
            income = periods[key]["income"]
            expenses = periods[key]["expenses"]
            net = income - expenses
            savings_rate = float(net / income * 100) if income > 0 else 0.0
            series.append(
                CashFlowPeriod(
                    period=key, income=income, expenses=expenses, net=net, savings_rate=savings_rate
                )
            )

        total_income = sum((p.income for p in series), Decimal("0"))
        total_expenses = sum((p.expenses for p in series), Decimal("0"))
        total_net = total_income - total_expenses
        total_savings_rate = float(total_net / total_income * 100) if total_income > 0 else 0.0
        totals = CashFlowTotals(
            income=total_income,
            expenses=total_expenses,
            net=total_net,
            savings_rate=total_savings_rate,
        )
        retirement_total = sum(retirement.values(), Decimal("0"))
        retirement_income = RetirementIncomeBreakdown(
            social_security=retirement["social_security"],
            pension=retirement["pension"],
            rmd=retirement["rmd"],
            total=retirement_total,
            has_data=retirement_total > 0,
        )
        return CashFlowReport(series=series, totals=totals, retirement_income=retirement_income)

    # --- Savings rate ----------------------------------------------------

    async def savings_rate(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
    ) -> SavingsRateReport:
        """Monthly savings rate ((income - expenses) / income) with a trailing
        3-month rolling average. The single biggest lever on time-to-FI, which
        the cash-flow report buries among per-period income/expense detail."""
        accounts = await self._visible_accounts(ctx)
        account_ids = [a.id for a in accounts]
        if not account_ids:
            return SavingsRateReport(
                series=[], average_rate=0.0, best_period=None, worst_period=None
            )

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
            key = _period_key(txn_date)
            if is_income:
                periods[key]["income"] += amount
            elif amount < 0:
                periods[key]["expenses"] += -amount

        ordered_keys = sorted(periods)
        rates: list[float] = []
        series: list[SavingsRatePoint] = []
        for key in ordered_keys:
            income = periods[key]["income"]
            expenses = periods[key]["expenses"]
            savings = income - expenses
            rate = float(savings / income * 100) if income > 0 else 0.0
            rates.append(rate)
            rolling = sum(rates[-3:]) / len(rates[-3:])
            series.append(
                SavingsRatePoint(
                    period=key,
                    income=income,
                    expenses=expenses,
                    savings=savings,
                    savings_rate=rate,
                    rolling_rate=rolling,
                )
            )

        total_income = sum((p.income for p in series), Decimal("0"))
        total_savings = sum((p.savings for p in series), Decimal("0"))
        average_rate = float(total_savings / total_income * 100) if total_income > 0 else 0.0
        best = max(series, key=lambda p: p.savings_rate).period if series else None
        worst = min(series, key=lambda p: p.savings_rate).period if series else None
        return SavingsRateReport(
            series=series,
            average_rate=average_rate,
            best_period=best,
            worst_period=worst,
        )

    # --- Budget vs actuals trend -----------------------------------------

    async def budget_vs_actuals_trend(
        self,
        ctx: VisibilityContext,
        from_date: date,
        to_date: date,
    ) -> BudgetTrendReport:
        """Total budgeted vs actual spend per month across a window. The Budgets
        tab shows a per-category table for a chosen range; this surfaces the
        whole-household variance as a trend so over/under months stand out."""
        series: list[BudgetTrendPoint] = []
        for month_end in _month_ends(from_date, to_date):
            month_str = _period_key(month_end)
            report = await self.budget_vs_actuals(ctx, month_str)
            budget = sum((item.budget for item in report.categories), Decimal("0"))
            actual = sum((item.actual for item in report.categories), Decimal("0"))
            series.append(
                BudgetTrendPoint(
                    period=month_str,
                    budget=budget,
                    actual=actual,
                    variance=budget - actual,
                )
            )

        total_budget = sum((p.budget for p in series), Decimal("0"))
        total_actual = sum((p.actual for p in series), Decimal("0"))
        return BudgetTrendReport(
            series=series,
            total_budget=total_budget,
            total_actual=total_actual,
            total_variance=total_budget - total_actual,
        )

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

        # Build a child→parent index for rollup when showing top-level categories.
        children_by_parent: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        if parent_category_id is None:
            for c in cat_map.values():
                if c.parent_category_id is not None:
                    children_by_parent[c.parent_category_id].append(c.id)

        items = []
        for c in target_categories:
            amount, count = sums.get(c.id, (Decimal("0"), 0))
            # Roll up child category amounts into the parent total.
            for child_id in children_by_parent.get(c.id, []):
                child_amount, child_count = sums.get(child_id, (Decimal("0"), 0))
                amount += child_amount
                count += child_count
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
            # Annual budgets are prorated to a monthly amount for comparison
            monthly_budget = (
                (budget.amount / Decimal("12")).quantize(Decimal("0.01"))
                if budget.period == "annual"
                else budget.amount
            )
            remaining = monthly_budget - actual
            pct = float(actual / monthly_budget * 100) if monthly_budget > 0 else 0.0
            best[category_id] = BudgetVsActualsItem(
                category_id=category_id,
                name=category.name if category else "Unknown",
                budget=monthly_budget,
                actual=actual,
                remaining=remaining,
                percentage_used=pct,
                period=budget.period,  # type: ignore[arg-type]
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
