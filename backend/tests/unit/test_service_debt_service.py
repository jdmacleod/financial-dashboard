from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.debt import Debt
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.account import AccountCreate, AccountType
from app.services.account import AccountService
from app.services.debt_service import DebtService


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
    account_type: AccountType = "mortgage",
    nickname: str = "Home Loan",
) -> Any:
    svc = AccountService(db_session)
    return await svc.create(ctx, AccountCreate(account_type=account_type, nickname=nickname))


async def _make_debt(
    db_session: AsyncSession,
    account_id: Any,
    current_balance: str = "200000",
    interest_rate: str = "0.065",
    minimum_payment: str = "1200",
) -> Debt:
    now = datetime.now(UTC)
    debt = Debt(
        account_id=account_id,
        original_balance=Decimal(current_balance),
        current_balance=Decimal(current_balance),
        interest_rate=Decimal(interest_rate),
        minimum_payment=Decimal(minimum_payment),
        created_at=now,
        updated_at=now,
    )
    db_session.add(debt)
    await db_session.flush()
    return debt


async def test_list_with_accounts_empty(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = DebtService(db_session)
    result = await svc.list_with_accounts(ctx)
    assert result == []


async def test_list_with_accounts_returns_debt(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx)
    await _make_debt(db_session, account.id, current_balance="150000", interest_rate="0.05")

    svc = DebtService(db_session)
    result = await svc.list_with_accounts(ctx)

    assert len(result) == 1
    assert result[0].current_balance == Decimal("150000")
    assert result[0].interest_rate == Decimal("0.05")
    assert result[0].nickname == "Home Loan"
    assert result[0].account_id == account.id


async def test_list_with_accounts_multiple_debts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    mortgage = await _make_account(db_session, ctx, account_type="mortgage", nickname="Mortgage")
    auto = await _make_account(db_session, ctx, account_type="auto_loan", nickname="Car Loan")
    await _make_debt(db_session, mortgage.id, current_balance="250000", interest_rate="0.04")
    await _make_debt(db_session, auto.id, current_balance="18000", interest_rate="0.06")

    svc = DebtService(db_session)
    result = await svc.list_with_accounts(ctx)

    assert len(result) == 2
    nicknames = {r.nickname for r in result}
    assert nicknames == {"Mortgage", "Car Loan"}


async def test_get_payoff_comparison_no_debts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    svc = DebtService(db_session)
    result = await svc.get_payoff_comparison(ctx)

    assert result.debts == []
    assert result.avalanche.months_to_payoff == 0
    assert result.snowball.months_to_payoff == 0


async def test_get_payoff_comparison_with_debt(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(db_session, ctx, account_type="personal_loan", nickname="Loan")
    await _make_debt(
        db_session,
        account.id,
        current_balance="5000",
        interest_rate="0.10",
        minimum_payment="200",
    )

    svc = DebtService(db_session)
    result = await svc.get_payoff_comparison(ctx)

    assert len(result.debts) == 1
    assert result.avalanche.strategy == "avalanche"
    assert result.snowball.strategy == "snowball"
    assert result.avalanche.months_to_payoff > 0
    assert result.snowball.months_to_payoff > 0
    # Single debt: both strategies produce same result
    assert result.avalanche.months_to_payoff == result.snowball.months_to_payoff


async def test_get_payoff_comparison_with_extra_payment(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, "primary", primary_user)
    account = await _make_account(
        db_session, ctx, account_type="student_loan", nickname="Student Loan"
    )
    await _make_debt(
        db_session,
        account.id,
        current_balance="20000",
        interest_rate="0.07",
        minimum_payment="300",
    )

    svc = DebtService(db_session)
    no_extra = await svc.get_payoff_comparison(ctx, extra_monthly_payment=Decimal(0))
    with_extra = await svc.get_payoff_comparison(ctx, extra_monthly_payment=Decimal(500))

    assert with_extra.avalanche.months_to_payoff < no_extra.avalanche.months_to_payoff
    assert with_extra.avalanche.total_interest_paid < no_extra.avalanche.total_interest_paid


async def test_get_payoff_comparison_avalanche_vs_snowball(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Avalanche pays less interest than snowball when rates differ and balances diverge.

    Avalanche targets the HIGH-rate debt first (credit card).
    Snowball targets the LOW-balance debt first (personal loan).
    These must be DIFFERENT debts to produce different interest totals.
    """
    ctx = _ctx(household, primary_member, "primary", primary_user)
    # High-rate, large balance — avalanche targets this first
    credit_card = await _make_account(
        db_session, ctx, account_type="credit_card", nickname="Credit Card"
    )
    # Low-rate, small balance — snowball targets this first
    small_loan = await _make_account(
        db_session, ctx, account_type="personal_loan", nickname="Small Loan"
    )
    await _make_debt(
        db_session,
        credit_card.id,
        current_balance="8000",  # large balance, high rate
        interest_rate="0.22",
        minimum_payment="200",
    )
    await _make_debt(
        db_session,
        small_loan.id,
        current_balance="500",  # small balance, low rate
        interest_rate="0.04",
        minimum_payment="50",
    )

    svc = DebtService(db_session)
    result = await svc.get_payoff_comparison(ctx, extra_monthly_payment=Decimal(300))

    # Avalanche targets $8000/22% card first → pays less total interest
    assert result.avalanche.total_interest_paid < result.snowball.total_interest_paid
