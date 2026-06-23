"""Unit tests for the investment positions rollup (Top positions + Holdings mix)."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.schemas.account import AccountCreate
from app.schemas.investment_lot import InvestmentLotCreate
from app.services.account import AccountService
from app.services.investment_lot import InvestmentLotService


def _ctx(household: Household, member: HouseholdMember, user: User) -> VisibilityContext:
    return VisibilityContext(
        user_id=user.id,
        member_id=member.id,
        role="primary",
        household_id=household.id,
    )


async def _brokerage(svc: AccountService, ctx: VisibilityContext, name: str):
    return await svc.create(ctx, AccountCreate(account_type="investment_brokerage", nickname=name))


async def test_positions_summary_rolls_up_by_ticker_and_asset_class(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account_svc = AccountService(db_session)
    acct_a = await _brokerage(account_svc, ctx, "Brokerage A")
    acct_b = await _brokerage(account_svc, ctx, "Brokerage B")

    lot_svc = InvestmentLotService(db_session)
    # VTI: two lots across two accounts -> aggregated into one position.
    await lot_svc.create(
        ctx,
        InvestmentLotCreate(
            account_id=acct_a.id,
            ticker="VTI",
            shares=Decimal("30"),
            basis_per_share=Decimal("200"),  # 6,000
            acquired_date=date(2022, 1, 1),
            basis_type="purchase",
            asset_class="equity",
        ),
    )
    await lot_svc.create(
        ctx,
        InvestmentLotCreate(
            account_id=acct_b.id,
            ticker="VTI",
            shares=Decimal("12"),
            basis_per_share=Decimal("250"),  # 3,000
            acquired_date=date(2023, 1, 1),
            basis_type="purchase",
            asset_class="equity",
        ),
    )
    # BND: one fixed-income lot.
    await lot_svc.create(
        ctx,
        InvestmentLotCreate(
            account_id=acct_a.id,
            ticker="BND",
            shares=Decimal("100"),
            basis_per_share=Decimal("10"),  # 1,000
            acquired_date=date(2023, 6, 1),
            basis_type="purchase",
            asset_class="fixed_income",
        ),
    )

    summary = await lot_svc.positions_summary(ctx)

    assert summary.total_cost_basis == Decimal("10000")

    # Positions ranked by cost basis, VTI first.
    assert [p.ticker for p in summary.positions] == ["VTI", "BND"]
    vti = summary.positions[0]
    assert vti.shares == Decimal("42")
    assert vti.cost_basis == Decimal("9000")
    assert vti.lot_count == 2

    # Holdings mix by asset class.
    mix = {s.asset_class: s for s in summary.holdings_mix}
    assert mix["equity"].cost_basis == Decimal("9000")
    assert mix["equity"].percentage == 90.0
    assert mix["fixed_income"].cost_basis == Decimal("1000")
    assert mix["fixed_income"].percentage == 10.0


async def test_positions_summary_unclassified_bucket(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    account_svc = AccountService(db_session)
    acct = await _brokerage(account_svc, ctx, "Brokerage")
    lot_svc = InvestmentLotService(db_session)
    await lot_svc.create(
        ctx,
        InvestmentLotCreate(
            account_id=acct.id,
            ticker="MYSTERY",
            shares=Decimal("5"),
            basis_per_share=Decimal("100"),
            acquired_date=date(2024, 1, 1),
            basis_type="purchase",
            # no asset_class
        ),
    )

    summary = await lot_svc.positions_summary(ctx)
    assert summary.holdings_mix[0].asset_class == "unclassified"
    assert summary.holdings_mix[0].cost_basis == Decimal("500")


async def test_positions_summary_empty(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    ctx = _ctx(household, primary_member, primary_user)
    summary = await InvestmentLotService(db_session).positions_summary(ctx)
    assert summary.positions == []
    assert summary.holdings_mix == []
    assert summary.total_cost_basis == Decimal("0")
