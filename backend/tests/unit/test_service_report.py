from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.real_estate import PropertyCreate, ValuationCreate
from app.services.account import AccountService
from app.services.real_estate import RealEstateService
from app.services.report import ReportService


def _ctx(
    household: Household, member: HouseholdMember, user: User, role: str = "primary"
) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


def _now() -> datetime:
    return datetime.now(UTC)


async def _make_account(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    account_type: str = "checking",
    nickname: str = "Test",
) -> Any:
    svc = AccountService(db_session)
    return await svc.create(ctx, AccountCreate(account_type=account_type, nickname=nickname))  # type: ignore[arg-type]


async def _add_snapshot(
    db_session: AsyncSession,
    account_id: uuid.UUID,
    snapshot_date: date,
    balance: Decimal,
) -> AccountSnapshot:
    snap = AccountSnapshot(
        account_id=account_id,
        snapshot_date=snapshot_date,
        balance=balance,
        source="manual",
        created_at=_now(),
    )
    db_session.add(snap)
    await db_session.flush()
    return snap


async def _add_transaction(
    db_session: AsyncSession,
    account_id: uuid.UUID,
    txn_date: date,
    amount: Decimal,
    category_id: uuid.UUID | None = None,
    real_estate_property_id: uuid.UUID | None = None,
) -> Transaction:
    txn = Transaction(
        account_id=account_id,
        transaction_date=txn_date,
        amount=amount,
        is_transfer=False,
        tags=[],
        source="manual",
        category_id=category_id,
        real_estate_property_id=real_estate_property_id,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(txn)
    await db_session.flush()
    return txn


async def _add_category(
    db_session: AsyncSession,
    household_id: uuid.UUID,
    name: str,
    is_income: bool = False,
    parent_category_id: uuid.UUID | None = None,
) -> Category:
    cat = Category(
        household_id=household_id,
        name=name,
        is_income=is_income,
        is_system=False,
        parent_category_id=parent_category_id,
        created_at=_now(),
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


# ---------------------------------------------------------------------------
# Net-worth tests
# ---------------------------------------------------------------------------


async def test_net_worth_with_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Checking")
    await _add_snapshot(db_session, account.id, date(2025, 1, 31), Decimal("5000"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    point = report.series[0]
    assert point.total_assets == Decimal("5000")
    assert point.total_liabilities == Decimal("0")
    assert point.net_worth == Decimal("5000")


async def test_net_worth_with_running_balance(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Checking No Snap")
    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("1000"))
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-200"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    point = report.series[0]
    assert point.total_assets == Decimal("800")


async def test_net_worth_quarterly_interval(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Q Account")
    for mo, bal in [(1, "1000"), (2, "2000"), (3, "3000"), (4, "4000"), (5, "5000"), (6, "6000")]:
        import calendar

        last_day = calendar.monthrange(2025, mo)[1]
        await _add_snapshot(db_session, account.id, date(2025, mo, last_day), Decimal(bal))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 6, 30), interval="quarterly")

    assert len(report.series) == 2
    assert report.series[0].date == date(2025, 3, 31)
    assert report.series[1].date == date(2025, 6, 30)


async def test_net_worth_annual_interval(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "savings", "Annual Account")
    await _add_snapshot(db_session, account.id, date(2025, 12, 31), Decimal("9999"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 12, 31), interval="annual")

    assert len(report.series) == 1
    assert report.series[0].date == date(2025, 12, 31)
    assert report.series[0].total_assets == Decimal("9999")


async def test_net_worth_empty_range_uses_to_date(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Fallback Account")
    await _add_snapshot(db_session, account.id, date(2025, 2, 28), Decimal("1234"))

    svc = ReportService(db_session)
    # Feb 28 is not a quarter-end → month_ends filtered to [] → fallback to to_date
    report = await svc.net_worth(ctx, date(2025, 2, 28), date(2025, 2, 28), interval="quarterly")

    assert len(report.series) == 1
    assert report.series[0].date == date(2025, 2, 28)


async def test_liability_with_debt_record(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "mortgage", "Mortgage")
    debt = Debt(
        account_id=account.id,
        original_balance=Decimal("300000"),
        current_balance=Decimal("298000"),
        interest_rate=Decimal("4.5"),
        minimum_payment=Decimal("1500"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    assert report.series[0].total_liabilities == Decimal("298000")


async def test_liability_credit_card_with_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "credit_card", "Visa")
    # Credit card balance typically stored as negative
    await _add_snapshot(db_session, account.id, date(2025, 1, 31), Decimal("-500"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    assert report.series[0].total_liabilities == Decimal("500")
    assert report.series[0].total_assets == Decimal("0")


async def test_liability_without_snapshot_or_debt(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    await _make_account(db_session, ctx, "mortgage", "Empty Mortgage")

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_liabilities == Decimal("0")


async def test_asset_non_cash_without_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "investment_brokerage", "Brokerage")
    # Add transactions — should NOT be used for non-cash accounts without a snapshot
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("9999"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    # No snapshot → value is 0 (not the running txn balance)
    assert report.series[0].total_assets == Decimal("0")


async def test_real_estate_value_flows_into_net_worth(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "real_estate", "My Home")

    re_svc = RealEstateService(db_session)
    prop = await re_svc.create(ctx, PropertyCreate(account_id=account.id, address="1 Test St"))
    await re_svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 15), estimated_value=Decimal("450000")),
    )

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_assets == Decimal("450000")
    assert report.series[0].breakdown.real_estate == Decimal("450000")
    assert report.series[0].net_worth == Decimal("450000")


async def test_real_estate_zero_when_no_valuation(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "real_estate", "Empty Lot")

    re_svc = RealEstateService(db_session)
    await re_svc.create(ctx, PropertyCreate(account_id=account.id, address="2 Test St"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_assets == Decimal("0")
    assert report.series[0].breakdown.real_estate == Decimal("0")


async def test_real_estate_account_without_property_record_returns_zero(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    # Create a real_estate account but deliberately skip RealEstateService.create
    # so no PropertyRecord exists — simulates data-integrity gap.
    await _make_account(db_session, ctx, "real_estate", "Orphan RE")

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_assets == Decimal("0")
    assert report.series[0].breakdown.real_estate == Decimal("0")


async def test_real_estate_as_of_date_filters_future_valuations(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "real_estate", "Growing Home")

    re_svc = RealEstateService(db_session)
    prop = await re_svc.create(ctx, PropertyCreate(account_id=account.id, address="3 Test St"))
    # Jan valuation — in-period for Jan report
    await re_svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 1, 15), estimated_value=Decimal("300000")),
    )
    # June valuation — must NOT appear in Jan net worth
    await re_svc.add_valuation(
        ctx,
        prop.id,
        ValuationCreate(valuation_date=date(2025, 6, 1), estimated_value=Decimal("350000")),
    )

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].breakdown.real_estate == Decimal("300000")


# ---------------------------------------------------------------------------
# Cash flow tests
# ---------------------------------------------------------------------------


async def test_cash_flow_with_transactions(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Cash Flow Checking")
    income_cat = await _add_category(db_session, household.id, "Salary", is_income=True)
    expense_cat = await _add_category(db_session, household.id, "Groceries", is_income=False)

    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("2000"), income_cat.id)
    await _add_transaction(
        db_session, account.id, date(2025, 1, 15), Decimal("1500"), income_cat.id
    )
    await _add_transaction(
        db_session, account.id, date(2025, 1, 8), Decimal("-300"), expense_cat.id
    )
    await _add_transaction(
        db_session, account.id, date(2025, 1, 20), Decimal("-150"), expense_cat.id
    )

    svc = ReportService(db_session)
    report = await svc.cash_flow(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.totals.income == Decimal("3500")
    assert report.totals.expenses == Decimal("450")
    assert report.totals.net == Decimal("3050")
    assert len(report.series) == 1
    assert report.series[0].period == "2025-01"


async def test_cash_flow_empty_accounts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    svc = ReportService(db_session)
    report = await svc.cash_flow(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series == []
    assert report.totals.income == Decimal("0")
    assert report.totals.expenses == Decimal("0")


async def test_cash_flow_quarter_grouping(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Q Checking")
    income_cat = await _add_category(db_session, household.id, "Q Income", is_income=True)

    await _add_transaction(
        db_session, account.id, date(2025, 1, 10), Decimal("1000"), income_cat.id
    )
    await _add_transaction(
        db_session, account.id, date(2025, 2, 14), Decimal("1000"), income_cat.id
    )
    await _add_transaction(
        db_session, account.id, date(2025, 3, 22), Decimal("1000"), income_cat.id
    )

    svc = ReportService(db_session)
    report = await svc.cash_flow(ctx, date(2025, 1, 1), date(2025, 3, 31), group_by="quarter")

    assert len(report.series) == 1
    assert report.series[0].period == "2025-Q1"
    assert report.series[0].income == Decimal("3000")


# ---------------------------------------------------------------------------
# Spending by category tests
# ---------------------------------------------------------------------------


async def test_spending_by_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Spend Checking")
    food_cat = await _add_category(db_session, household.id, "Food")
    transport_cat = await _add_category(db_session, household.id, "Transport")

    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("-400"), food_cat.id)
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-100"), food_cat.id)
    await _add_transaction(
        db_session, account.id, date(2025, 1, 15), Decimal("-200"), transport_cat.id
    )

    svc = ReportService(db_session)
    report = await svc.spending_by_category(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.total == Decimal("700")
    names = {item.name for item in report.categories}
    assert "Food" in names
    assert "Transport" in names
    food_item = next(i for i in report.categories if i.name == "Food")
    assert food_item.amount == Decimal("500")
    assert food_item.transaction_count == 2


async def test_spending_by_category_empty_accounts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    svc = ReportService(db_session)
    report = await svc.spending_by_category(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.total == Decimal("0")
    assert report.categories == []


async def test_spending_by_category_with_parent(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Parent Cat Checking")
    parent_cat = await _add_category(db_session, household.id, "Dining Out")
    child1 = await _add_category(
        db_session, household.id, "Restaurants", parent_category_id=parent_cat.id
    )
    child2 = await _add_category(
        db_session, household.id, "Fast Food", parent_category_id=parent_cat.id
    )
    # Unrelated top-level category — should not appear
    await _add_category(db_session, household.id, "Groceries")

    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("-60"), child1.id)
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-20"), child2.id)

    svc = ReportService(db_session)
    report = await svc.spending_by_category(
        ctx, date(2025, 1, 1), date(2025, 1, 31), parent_category_id=parent_cat.id
    )

    names = {item.name for item in report.categories}
    assert names == {"Restaurants", "Fast Food"}
    assert report.total == Decimal("80")


async def test_spending_includes_uncategorized(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Uncat Checking")
    # Transaction with no category_id
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-75"))

    svc = ReportService(db_session)
    report = await svc.spending_by_category(ctx, date(2025, 1, 1), date(2025, 1, 31))

    names = [item.name for item in report.categories]
    assert "Uncategorized" in names
    uncat = next(i for i in report.categories if i.name == "Uncategorized")
    assert uncat.amount == Decimal("75")


# ---------------------------------------------------------------------------
# Budget vs actuals tests
# ---------------------------------------------------------------------------


async def test_budget_vs_actuals(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Budget Checking")
    cat = await _add_category(db_session, household.id, "Entertainment")

    budget = Budget(
        household_id=household.id,
        category_id=cat.id,
        period="monthly",
        amount=Decimal("500"),
        effective_from=date(2025, 1, 1),
        effective_to=None,
    )
    db_session.add(budget)
    await db_session.flush()

    await _add_transaction(db_session, account.id, date(2025, 3, 15), Decimal("-450"), cat.id)

    svc = ReportService(db_session)
    report = await svc.budget_vs_actuals(ctx, "2025-03")

    assert len(report.categories) == 1
    item = report.categories[0]
    assert item.budget == Decimal("500")
    assert item.actual == Decimal("450")
    assert item.remaining == Decimal("50")
    assert item.name == "Entertainment"


async def test_budget_vs_actuals_no_budgets(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    svc = ReportService(db_session)
    report = await svc.budget_vs_actuals(ctx, "2025-03")
    assert report.categories == []


# ---------------------------------------------------------------------------
# Property P&L tests
# ---------------------------------------------------------------------------


async def test_property_pnl(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    re_acct = await _make_account(db_session, ctx, "real_estate", "Rental House")
    prop_resp = await RealEstateService(db_session).create(
        ctx, PropertyCreate(account_id=re_acct.id, address="123 Main St")
    )
    prop_id = prop_resp.id

    income_cat = await _add_category(db_session, household.id, "Rental Income", is_income=True)
    expense_cat = await _add_category(db_session, household.id, "Repairs")

    await _add_transaction(
        db_session,
        re_acct.id,
        date(2025, 3, 1),
        Decimal("2000"),
        income_cat.id,
        real_estate_property_id=prop_id,
    )
    await _add_transaction(
        db_session,
        re_acct.id,
        date(2025, 3, 15),
        Decimal("-400"),
        expense_cat.id,
        real_estate_property_id=prop_id,
    )

    svc = ReportService(db_session)
    report = await svc.property_pnl(ctx, prop_id, date(2025, 1, 1), date(2025, 3, 31))

    assert report.gross_income == Decimal("2000")
    assert report.total_expenses == Decimal("400")
    assert report.net_income == Decimal("1600")
    assert report.address == "123 Main St"
    assert len(report.expense_breakdown) == 1
    assert report.expense_breakdown[0].name == "Repairs"


async def test_property_pnl_not_found(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    svc = ReportService(db_session)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await svc.property_pnl(ctx, uuid.uuid4(), date(2025, 1, 1), date(2025, 1, 31))
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Dashboard test
# ---------------------------------------------------------------------------


async def test_dashboard(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Dashboard Checking")
    # Snapshot for today to give a net worth value
    today = date.today()
    await _add_snapshot(db_session, account.id, today, Decimal("10000"))

    income_cat = await _add_category(db_session, household.id, "Dash Income", is_income=True)
    expense_cat = await _add_category(db_session, household.id, "Dash Expense")

    month_start = today.replace(day=1)
    await _add_transaction(db_session, account.id, month_start, Decimal("3000"), income_cat.id)
    await _add_transaction(db_session, account.id, month_start, Decimal("-200"), expense_cat.id)

    svc = ReportService(db_session)
    response = await svc.dashboard(ctx)

    assert response.net_worth.current == Decimal("10000")
    assert response.cash_flow_mtd.income == Decimal("3000")
    assert response.cash_flow_mtd.expenses == Decimal("200")
    assert isinstance(response.top_spending_categories, list)
    assert isinstance(response.budget_alerts, list)
    assert response.accounts_summary.total_assets == Decimal("10000")
