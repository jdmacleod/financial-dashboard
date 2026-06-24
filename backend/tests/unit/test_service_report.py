from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.budget import Budget
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionEstimateHistory
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.repositories.pension import PensionRepository
from app.schemas.account import AccountCreate
from app.schemas.pension import PensionAccountCreate
from app.schemas.real_estate import PropertyCreate, ValuationCreate
from app.services.account import AccountService
from app.services.pension import PensionService
from app.services.pension_valuation import pension_present_value
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
    slug: str | None = None,
) -> Category:
    cat = Category(
        household_id=household_id,
        name=name,
        slug=slug,
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


async def test_liability_credit_card_uses_transaction_sum(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # Credit card balances come from transaction sums, not snapshots.
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "credit_card", "Visa")
    # Purchases are negative; balance owed = abs(running sum).
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-300"))
    await _add_transaction(db_session, account.id, date(2025, 1, 20), Decimal("-200"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    assert report.series[0].total_liabilities == Decimal("500")
    assert report.series[0].total_assets == Decimal("0")


async def test_liability_heloc_uses_transaction_sum(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # HELOC balances come from running transaction sums, matching credit_card behaviour.
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "heloc", "Chase HELOC")
    # Draws are negative; the abs() of the sum is reported as the liability.
    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("-20000"))
    await _add_transaction(db_session, account.id, date(2025, 1, 15), Decimal("-5000"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.series) == 1
    assert report.series[0].total_liabilities == Decimal("25000")
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


async def test_tracked_loan_amortizes_over_time_and_beats_stale_debt(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # A transaction-tracked consumer loan must value from the running transaction
    # sum at each date so the liability amortizes as payments post — not a flat
    # line from a static Debt.current_balance. Regression for the Park-Cole bug
    # where student loans showed an unchanging $59,500 across 24 months.
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "student_loan", "MOHELA")
    # Opening balance of $10,000 owed, then two $1,000 payments.
    await _add_transaction(db_session, account.id, date(2024, 12, 31), Decimal("-10000"))
    await _add_transaction(db_session, account.id, date(2025, 1, 15), Decimal("1000"))
    await _add_transaction(db_session, account.id, date(2025, 2, 15), Decimal("1000"))
    # A stale Debt record that disagrees with the transactions: the report must
    # prefer the transaction-derived balance over this figure.
    debt = Debt(
        account_id=account.id,
        original_balance=Decimal("12000"),
        current_balance=Decimal("9999"),
        interest_rate=Decimal("5.5"),
        minimum_payment=Decimal("275"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 3, 31))

    liabilities = [p.total_liabilities for p in report.series]
    # Jan: 10000 - 1000 = 9000; Feb: 8000; Mar: 8000 (no March payment).
    assert liabilities == [Decimal("9000"), Decimal("8000"), Decimal("8000")]
    # The stale Debt figure must NOT appear and the line must move over time.
    assert Decimal("9999") not in liabilities
    assert liabilities[0] != liabilities[1]


async def test_tracked_loan_without_transactions_falls_back_to_debt(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # A consumer loan tracked only by a structured Debt record (no transactions
    # to anchor the balance) still reports the Debt.current_balance.
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "auto_loan", "Tennessee CU")
    debt = Debt(
        account_id=account.id,
        original_balance=Decimal("18500"),
        current_balance=Decimal("14800"),
        interest_rate=Decimal("6.9"),
        minimum_payment=Decimal("312"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_liabilities == Decimal("14800")


async def test_sbloc_amortizes_via_transactions_even_with_a_debt_record(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # Revolving lines (SBLOC / margin) are transaction-tracked: a draw raises the
    # balance, a paydown lowers it, and the report follows the running sum at each
    # date. Attaching a Debt record must NOT pin the line to a single static value
    # (the flat-line bug fixed for student/auto loans applies to these too).
    ctx = _ctx(household, primary_member, primary_user)
    # sbloc is a demo-data-extension type the AccountCreate schema doesn't accept,
    # so build the model directly rather than via _make_account.
    account = Account(
        household_id=ctx.household_id,
        account_type="sbloc",
        nickname="Pledged-Asset Line",
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()
    # $100k draw, then a $20k paydown the next month.
    await _add_transaction(db_session, account.id, date(2025, 1, 10), Decimal("-100000"))
    await _add_transaction(db_session, account.id, date(2025, 2, 10), Decimal("20000"))
    # A stale Debt record that disagrees — the report must ignore it in favor of
    # the transaction-derived balance.
    debt = Debt(
        account_id=account.id,
        original_balance=Decimal("100000"),
        current_balance=Decimal("99999"),
        interest_rate=Decimal("6.0"),
        minimum_payment=Decimal("0"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 2, 28))

    liabilities = [p.total_liabilities for p in report.series]
    # Jan: 100000; Feb after the paydown: 80000.
    assert liabilities == [Decimal("100000"), Decimal("80000")]
    assert Decimal("99999") not in liabilities


async def test_txn_tracked_liability_falls_back_to_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # A transaction-tracked liability with neither transactions nor a Debt record
    # but a balance snapshot reports the snapshot value (a line of credit imported
    # as a balance with no transaction history). Guards the snapshot fallback that
    # adding sbloc/margin to the TXN_TRACKED branch could otherwise have dropped.
    ctx = _ctx(household, primary_member, primary_user)
    account = Account(
        household_id=ctx.household_id,
        account_type="margin",
        nickname="Margin Account",
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()
    await _add_snapshot(db_session, account.id, date(2025, 1, 31), Decimal("50000"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.series[0].total_liabilities == Decimal("50000")


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
# Pension PV tests (B2 — Phase 8)
# ---------------------------------------------------------------------------

PENSION_DISCOUNT = Decimal("0.04")


async def _make_pension_account(
    db_session: AsyncSession, ctx: VisibilityContext, monthly_benefit: Decimal | None
) -> Any:
    account_svc = AccountService(db_session)
    account = await account_svc.create(
        ctx, AccountCreate(account_type="pension", nickname="State Pension")
    )
    pension_svc = PensionService(db_session)
    await pension_svc.create(
        ctx,
        account.id,
        PensionAccountCreate(
            plan_name="State Retirement System",
            monthly_benefit_estimate=monthly_benefit,
            is_vested=True,
        ),
    )
    return account


async def test_asset_value_at_pension_uses_pv(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_pension_account(db_session, ctx, Decimal("3000.00"))

    svc = ReportService(db_session)
    point = await svc.current_net_worth(ctx, date(2025, 6, 30))

    pension = await PensionRepository(db_session).get_by_account_id(account.id)
    expected_pv = pension_present_value(pension, date(2025, 6, 30))
    assert expected_pv > 0
    # A finite life annuity is worth less than the old perpetuity (annual / 0.04).
    assert expected_pv < Decimal("3000.00") * 12 / PENSION_DISCOUNT
    assert point.total_assets == expected_pv
    assert point.breakdown.retirement == expected_pv


async def test_asset_value_at_pension_no_estimate_returns_zero(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    await _make_pension_account(db_session, ctx, None)

    svc = ReportService(db_session)
    point = await svc.current_net_worth(ctx, date(2025, 6, 30))

    assert point.total_assets == Decimal("0")
    assert point.breakdown.retirement == Decimal("0")


async def test_current_net_worth_includes_pension_pv(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    checking = await _make_account(db_session, ctx, "checking", "Checking")
    await _add_snapshot(db_session, checking.id, date(2025, 6, 30), Decimal("10000"))
    account = await _make_pension_account(db_session, ctx, Decimal("2000.00"))

    svc = ReportService(db_session)
    point = await svc.current_net_worth(ctx, date(2025, 6, 30))

    pension = await PensionRepository(db_session).get_by_account_id(account.id)
    pension_pv = pension_present_value(pension, date(2025, 6, 30))
    assert point.total_assets == Decimal("10000") + pension_pv
    assert point.breakdown.checking_savings == Decimal("10000")
    assert point.breakdown.retirement == pension_pv


async def test_net_worth_time_series_pension_pv(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_pension_account(db_session, ctx, Decimal("1500.00"))

    svc = ReportService(db_session)
    # Two monthly points — pension PV should appear in both
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 2, 28))

    # No eligibility date on this pension, so its PV is constant across points.
    pension = await PensionRepository(db_session).get_by_account_id(account.id)
    expected_pv = pension_present_value(pension, date(2025, 2, 28))
    assert len(report.series) == 2
    assert report.series[0].breakdown.retirement == expected_pv
    assert report.series[1].breakdown.retirement == expected_pv
    assert report.series[0].total_assets == expected_pv
    assert report.series[1].total_assets == expected_pv


async def test_net_worth_pension_annotations_populated(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """pension_annotations on NetWorthReport lists pension account details for FIRE display."""
    ctx = _ctx(household, primary_member, primary_user)
    await _make_pension_account(db_session, ctx, Decimal("2500.00"))

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert len(report.pension_annotations) == 1
    ann = report.pension_annotations[0]
    assert ann.monthly_benefit == Decimal("2500.00")
    # PV is now surfaced on the annotation so the UI does not recompute it.
    assert ann.estimated_pv is not None
    assert ann.estimated_pv > 0


async def test_net_worth_uses_estimate_in_effect_per_date(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """A later estimate increase must NOT rewrite earlier net-worth points: each
    point is valued from the PensionEstimateHistory row in effect at that date."""
    ctx = _ctx(household, primary_member, primary_user)
    # Current estimate is $2500 (service also records a row effective today).
    account = await _make_pension_account(db_session, ctx, Decimal("2500.00"))
    pension = await PensionRepository(db_session).get_by_account_id(account.id)

    # Backdated history: $2000 from 2024, bumped to $2500 from June 2025.
    h_low = PensionEstimateHistory(
        pension_account_id=pension.id,
        effective_date=date(2024, 1, 1),
        monthly_benefit_estimate=Decimal("2000.00"),
        cola_adjustment_rate=Decimal("0.02"),
        survivor_benefit_percent=None,
        eligibility_date=None,
        created_at=_now(),
    )
    h_high = PensionEstimateHistory(
        pension_account_id=pension.id,
        effective_date=date(2025, 6, 1),
        monthly_benefit_estimate=Decimal("2500.00"),
        cola_adjustment_rate=Decimal("0.02"),
        survivor_benefit_percent=None,
        eligibility_date=None,
        created_at=_now(),
    )
    db_session.add_all([h_low, h_high])
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.net_worth(ctx, date(2025, 1, 1), date(2025, 12, 31), interval="quarterly")
    by_date = {p.date: p.breakdown.retirement for p in report.series}

    # Q1 2025 predates the bump → valued from the $2000 estimate, NOT the current $2500.
    assert by_date[date(2025, 3, 31)] == pension_present_value(h_low, date(2025, 3, 31))
    # Q4 2025 is after the bump → valued from the $2500 estimate.
    assert by_date[date(2025, 12, 31)] == pension_present_value(h_high, date(2025, 12, 31))
    assert by_date[date(2025, 12, 31)] > by_date[date(2025, 3, 31)]


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


async def test_cash_flow_retirement_income_breakdown(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Retiree Checking")
    ss_cat = await _add_category(
        db_session, household.id, "Social Security", is_income=True, slug="social_security_income"
    )
    pension_cat = await _add_category(
        db_session, household.id, "Pension Income", is_income=True, slug="pension_income"
    )
    rmd_cat = await _add_category(
        db_session,
        household.id,
        "Required Minimum Distribution",
        is_income=True,
        slug="rmd_distribution",
    )
    salary_cat = await _add_category(db_session, household.id, "Salary", is_income=True)

    await _add_transaction(db_session, account.id, date(2025, 1, 3), Decimal("4886"), ss_cat.id)
    await _add_transaction(
        db_session, account.id, date(2025, 1, 1), Decimal("4000"), pension_cat.id
    )
    await _add_transaction(db_session, account.id, date(2025, 1, 15), Decimal("9000"), rmd_cat.id)
    # Ordinary income should not land in any retirement bucket.
    await _add_transaction(
        db_session, account.id, date(2025, 1, 20), Decimal("1000"), salary_cat.id
    )

    svc = ReportService(db_session)
    report = await svc.cash_flow(ctx, date(2025, 1, 1), date(2025, 1, 31))

    ri = report.retirement_income
    assert ri.has_data is True
    assert ri.social_security == Decimal("4886")
    assert ri.pension == Decimal("4000")
    assert ri.rmd == Decimal("9000")
    assert ri.total == Decimal("17886")
    # Retirement buckets are a subset of total income.
    assert report.totals.income == Decimal("18886")


async def test_cash_flow_retirement_income_absent_when_no_retirement(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Worker Checking")
    salary_cat = await _add_category(db_session, household.id, "Salary", is_income=True)
    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("5000"), salary_cat.id)

    svc = ReportService(db_session)
    report = await svc.cash_flow(ctx, date(2025, 1, 1), date(2025, 1, 31))

    assert report.retirement_income.has_data is False
    assert report.retirement_income.total == Decimal("0")


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


async def test_budget_vs_actuals_annual_proration(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Annual budgets are prorated to monthly (÷12) when returned by the report."""
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Budget Checking Annual")
    cat = await _add_category(db_session, household.id, "HomeInsurance")

    annual_budget = Budget(
        household_id=household.id,
        category_id=cat.id,
        period="annual",
        amount=Decimal("1200"),
        effective_from=date(2025, 1, 1),
        effective_to=None,
    )
    db_session.add(annual_budget)
    await db_session.flush()

    await _add_transaction(db_session, account.id, date(2025, 3, 15), Decimal("-80"), cat.id)

    svc = ReportService(db_session)
    report = await svc.budget_vs_actuals(ctx, "2025-03")

    assert len(report.categories) == 1
    item = report.categories[0]
    # Annual $1200 prorated to monthly $100
    assert item.budget == Decimal("100.00")
    assert item.actual == Decimal("80")
    assert item.remaining == Decimal("20.00")
    assert item.period == "annual"
    assert item.name == "HomeInsurance"


async def test_budget_vs_actuals_period_field_propagated(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """The period field on BudgetVsActualsItem reflects the budget's period type."""
    ctx = _ctx(household, primary_member, primary_user)
    await _make_account(db_session, ctx, "checking", "Budget Checking Period")
    cat_m = await _add_category(db_session, household.id, "Groceries2")
    cat_a = await _add_category(db_session, household.id, "Insurance2")

    db_session.add(
        Budget(
            household_id=household.id,
            category_id=cat_m.id,
            period="monthly",
            amount=Decimal("500"),
            effective_from=date(2025, 1, 1),
        )
    )
    db_session.add(
        Budget(
            household_id=household.id,
            category_id=cat_a.id,
            period="annual",
            amount=Decimal("1200"),
            effective_from=date(2025, 1, 1),
        )
    )
    await db_session.flush()

    svc = ReportService(db_session)
    report = await svc.budget_vs_actuals(ctx, "2025-03")

    by_cat = {item.name: item for item in report.categories}
    assert by_cat["Groceries2"].period == "monthly"
    assert by_cat["Insurance2"].period == "annual"


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


async def test_savings_rate_series_and_rolling(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "SR Checking")
    income_cat = await _add_category(db_session, household.id, "Salary", is_income=True)
    expense_cat = await _add_category(db_session, household.id, "Rent")

    # Jan: income 4000, expenses 1000 -> rate 75%
    await _add_transaction(db_session, account.id, date(2025, 1, 5), Decimal("4000"), income_cat.id)
    await _add_transaction(
        db_session, account.id, date(2025, 1, 6), Decimal("-1000"), expense_cat.id
    )
    # Feb: income 4000, expenses 3000 -> rate 25%
    await _add_transaction(db_session, account.id, date(2025, 2, 5), Decimal("4000"), income_cat.id)
    await _add_transaction(
        db_session, account.id, date(2025, 2, 6), Decimal("-3000"), expense_cat.id
    )

    svc = ReportService(db_session)
    report = await svc.savings_rate(ctx, date(2025, 1, 1), date(2025, 2, 28))

    assert [p.period for p in report.series] == ["2025-01", "2025-02"]
    assert report.series[0].savings == Decimal("3000")
    assert report.series[0].savings_rate == pytest.approx(75.0)
    assert report.series[1].savings_rate == pytest.approx(25.0)
    # Rolling = trailing 3-month average: Feb sees (75 + 25) / 2 = 50.
    assert report.series[1].rolling_rate == pytest.approx(50.0)
    # Aggregate: total savings 4000 / total income 8000 = 50%.
    assert report.average_rate == pytest.approx(50.0)
    assert report.best_period == "2025-01"
    assert report.worst_period == "2025-02"


async def test_savings_rate_no_accounts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    svc = ReportService(db_session)
    report = await svc.savings_rate(ctx, date(2025, 1, 1), date(2025, 3, 31))
    assert report.series == []
    assert report.average_rate == 0.0
    assert report.best_period is None


async def test_budget_vs_actuals_trend(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account = await _make_account(db_session, ctx, "checking", "Trend Checking")
    cat = await _add_category(db_session, household.id, "Groceries")
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

    # Jan under budget (450), Feb over budget (560).
    await _add_transaction(db_session, account.id, date(2025, 1, 15), Decimal("-450"), cat.id)
    await _add_transaction(db_session, account.id, date(2025, 2, 15), Decimal("-560"), cat.id)

    svc = ReportService(db_session)
    report = await svc.budget_vs_actuals_trend(ctx, date(2025, 1, 1), date(2025, 2, 28))

    assert [p.period for p in report.series] == ["2025-01", "2025-02"]
    assert report.series[0].budget == Decimal("500")
    assert report.series[0].actual == Decimal("450")
    assert report.series[0].variance == Decimal("50")
    assert report.series[1].variance == Decimal("-60")
    assert report.total_budget == Decimal("1000")
    assert report.total_actual == Decimal("1010")
    assert report.total_variance == Decimal("-10")
