from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.pension import PensionAccount
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.schemas.account import AccountCreate, AccountType
from app.schemas.fire import IncomeStreamType
from app.services.account import AccountService
from app.services.fire_detector import FireInputDetector, _map_category_to_stream_type


def _ctx(household: Household, member: HouseholdMember, role: str, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role=role,
        household_id=household.id,
    )


async def _make_account(
    db_session: AsyncSession,
    ctx: VisibilityContext,
    account_type: AccountType = "checking",
    nickname: str = "Checking",
) -> Any:
    return await AccountService(db_session).create(
        ctx, AccountCreate(account_type=account_type, nickname=nickname)
    )


async def _make_category(
    db_session: AsyncSession,
    household: Household,
    name: str = "Salary",
    is_income: bool = True,
) -> Category:
    cat = Category(
        household_id=household.id,
        name=name,
        is_income=is_income,
        is_system=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


async def _make_transaction(
    db_session: AsyncSession,
    account_id: Any,
    amount: str,
    txn_date: date | None = None,
    category_id: Any = None,
    is_transfer: bool = False,
) -> Transaction:
    now = datetime.now(UTC)
    txn = Transaction(
        account_id=account_id,
        transaction_date=txn_date or date(2025, 1, 15),
        amount=Decimal(amount),
        is_transfer=is_transfer,
        tags=[],
        source="manual",
        category_id=category_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(txn)
    await db_session.flush()
    return txn


# --- Pure function tests (no DB) ---


def test_map_category_salary() -> None:
    assert _map_category_to_stream_type("My Salary") == IncomeStreamType.salary
    assert _map_category_to_stream_type("Wages") == IncomeStreamType.salary
    assert _map_category_to_stream_type("Payroll") == IncomeStreamType.salary


def test_map_category_rental() -> None:
    assert _map_category_to_stream_type("Rental Income") == IncomeStreamType.rental
    assert _map_category_to_stream_type("Lease payments") == IncomeStreamType.rental


def test_map_category_consulting() -> None:
    assert _map_category_to_stream_type("Consulting fees") == IncomeStreamType.consulting
    assert _map_category_to_stream_type("Freelance work") == IncomeStreamType.consulting


def test_map_category_pension() -> None:
    assert _map_category_to_stream_type("Pension income") == IncomeStreamType.pension


def test_map_category_social_security() -> None:
    assert _map_category_to_stream_type("Social Security") == IncomeStreamType.social_security
    assert _map_category_to_stream_type("SSA benefit") == IncomeStreamType.social_security


def test_map_category_investment() -> None:
    assert _map_category_to_stream_type("Dividend income") == IncomeStreamType.investment
    assert _map_category_to_stream_type("Capital Gains") == IncomeStreamType.investment


def test_map_category_other() -> None:
    assert _map_category_to_stream_type("Miscellaneous") == IncomeStreamType.other


# --- DB integration tests ---


async def test_detect_empty_household(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Detect with no accounts returns empty result."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    assert result.income_streams == []
    assert result.gross_income_annual == Decimal(0)
    assert result.months_with_data == 0
    assert len(result.warnings) > 0  # warns about sparse data


async def test_detect_with_income_transactions(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Detect with income transactions builds income stream."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    cat = await _make_category(db_session, household, name="Salary", is_income=True)

    # 3 recent monthly income transactions (within trailing_months=12)
    today = date.today()
    for offset in [30, 60, 90]:
        await _make_transaction(
            db_session,
            account.id,
            "5000",
            today - timedelta(days=offset),
            category_id=cat.id,
        )

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    assert len(result.income_streams) == 1
    assert result.income_streams[0].label == "Salary"
    assert result.income_streams[0].auto_detected is True
    assert result.gross_income_annual > Decimal(0)


async def test_detect_expense_transactions(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Detect computes total_expenses_annual from non-income transactions."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    expense_cat = await _make_category(db_session, household, name="Groceries", is_income=False)

    today = date.today()
    for offset in [30, 60, 90]:
        await _make_transaction(
            db_session,
            account.id,
            "-500",
            today - timedelta(days=offset),
            category_id=expense_cat.id,
        )

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    assert result.total_expenses_annual > Decimal(0)


async def test_detect_portfolio_value_from_snapshot(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Detect reads portfolio value from latest snapshot of investment accounts."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    brokerage = await _make_account(
        db_session, ctx, account_type="investment_brokerage", nickname="Brokerage"
    )

    snap = AccountSnapshot(
        account_id=brokerage.id,
        snapshot_date=date(2025, 6, 30),
        balance=Decimal("75000"),
        source="manual",
        created_at=datetime.now(UTC),
    )
    db_session.add(snap)
    await db_session.flush()

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    assert result.current_portfolio_value == Decimal("75000")


async def test_detect_sparse_data_warning(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Detect with < 6 months of data emits a warning."""
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    cat = await _make_category(db_session, household, name="Wages", is_income=True)

    # Two transactions in different calendar months, always within 12-month window.
    # Using relative month arithmetic (not day offsets) avoids the edge case where
    # both timedelta dates land in the same month (e.g. June 20 - 20d = May 31,
    # June 20 - 50d = May 1 — both May, so months_with_data would be 1, not 2).
    today = date.today()
    prev_month_15 = (today.replace(day=1) - timedelta(days=1)).replace(day=15)
    two_months_ago_15 = (prev_month_15.replace(day=1) - timedelta(days=1)).replace(day=15)
    await _make_transaction(db_session, account.id, "4000", prev_month_15, category_id=cat.id)
    await _make_transaction(db_session, account.id, "4000", two_months_ago_15, category_id=cat.id)

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    assert any("months" in w.lower() for w in result.warnings)
    assert result.months_with_data == 2


# --- Pension stream detection ---


async def test_detect_pension_streams_vested(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="pension", nickname="Pension")
    pension = PensionAccount(
        account_id=uuid.UUID(str(account.id)),
        is_vested=True,
        monthly_benefit_estimate=Decimal("2000.00"),
        cola_adjustment_rate=Decimal("0.025"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pension)
    await db_session.flush()

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    pension_streams = [s for s in result.income_streams if s.type == IncomeStreamType.pension]
    assert len(pension_streams) == 1
    assert pension_streams[0].amount_annual == Decimal("24000.00")
    assert pension_streams[0].source_account_id is not None


async def test_detect_pension_streams_skips_none_benefit(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="pension", nickname="No Benefit")
    pension = PensionAccount(
        account_id=uuid.UUID(str(account.id)),
        is_vested=True,
        monthly_benefit_estimate=None,
        cola_adjustment_rate=Decimal("0.02"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pension)
    await db_session.flush()

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    pension_streams = [s for s in result.income_streams if s.type == IncomeStreamType.pension]
    assert len(pension_streams) == 0


async def test_detect_pension_start_year_from_eligibility_date(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="pension", nickname="Date Pension")
    pension = PensionAccount(
        account_id=uuid.UUID(str(account.id)),
        is_vested=True,
        monthly_benefit_estimate=Decimal("1500.00"),
        eligibility_date=date(2038, 6, 1),
        cola_adjustment_rate=Decimal("0.02"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pension)
    await db_session.flush()

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    pension_streams = [s for s in result.income_streams if s.type == IncomeStreamType.pension]
    assert len(pension_streams) == 1
    assert pension_streams[0].start_year == 2038


async def test_detect_pension_start_year_from_eligibility_age(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="pension", nickname="Age Pension")
    pension = PensionAccount(
        account_id=uuid.UUID(str(account.id)),
        is_vested=True,
        monthly_benefit_estimate=Decimal("1000.00"),
        eligibility_age=67,
        cola_adjustment_rate=Decimal("0.02"),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(pension)
    await db_session.flush()

    detector = FireInputDetector(db_session)
    result = await detector.detect(ctx, trailing_months=12)

    pension_streams = [s for s in result.income_streams if s.type == IncomeStreamType.pension]
    assert len(pension_streams) == 1
    # start_year = current_year + max(0, 67 - 65) = current_year + 2
    assert pension_streams[0].start_year == date.today().year + 2
