"""@audit services for the demo-data extension (spec Phase A AC #5/#6/#7/#8).

- A vesting event atomically creates a lot, an income transaction, and a
  sell-to-cover transfer, and writes an audit row.
- A capital call increases called_to_date, posts a capital_call transfer, and
  its audit row excludes the encrypted fund_name_enc column.
- An SBLOC draw posts a negative-amount sbloc_draw transfer with an audit row.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AUDIT_EXCLUDED_FIELDS
from app.core.encryption import encrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.audit_log import AuditLog
from app.db.models.capital_commitment import CapitalCommitment
from app.db.models.equity_grant import EquityGrant
from app.db.models.household import Household
from app.db.models.investment_lot import InvestmentLot
from app.db.models.member import HouseholdMember
from app.db.models.transaction import Transaction
from app.services.credit_line import CreditLineService, SblocPostingInput
from app.services.equity_comp import EquityCompService, VestingEventInput
from app.services.private_fund import CapitalCallInput, PrivateFundService


def _now() -> datetime:
    return datetime.now(UTC)


async def _account(session: AsyncSession, household_id, account_type: str) -> Account:
    acct = Account(
        household_id=household_id,
        account_type=account_type,
        nickname=account_type,
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(acct)
    await session.flush()
    return acct


async def _latest_audit_row(session: AsyncSession, action: str) -> AuditLog | None:
    result = await session.execute(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )
    return result.scalars().first()


async def _account_txns(session: AsyncSession, account_id) -> list[Transaction]:
    result = await session.execute(select(Transaction).where(Transaction.account_id == account_id))
    return list(result.scalars().all())


async def test_vesting_event_creates_lot_income_and_sell_to_cover(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    acct = await _account(db_session, household.id, "investment_brokerage")
    grant = EquityGrant(
        household_id=household.id,
        member_id=primary_member.id,
        grant_type="rsu",
        grant_date=date(2024, 1, 1),
        shares_granted=Decimal("400"),
        ticker="ACME",
        vesting_schedule={"cliff_months": 12, "cadence": "quarterly"},
        created_at=_now(),
    )
    db_session.add(grant)
    await db_session.flush()

    service = EquityCompService(db_session)
    event = await service.record_vesting_event(
        primary_ctx,
        VestingEventInput(
            account_id=acct.id,
            equity_grant_id=grant.id,
            event_date=date(2025, 3, 15),
            shares_vested=Decimal("100"),
            fmv_at_event=Decimal("50"),
            ticker="ACME",
            shares_sold_to_cover=Decimal("40"),
        ),
    )

    assert event.taxable_ordinary_income == Decimal("5000")
    assert event.resulting_lot_id is not None

    lot = await db_session.get(InvestmentLot, event.resulting_lot_id)
    assert lot is not None
    assert lot.shares == Decimal("60")  # 100 vested - 40 sold to cover
    assert lot.basis_per_share == Decimal("50")
    assert lot.basis_type == "rsu_vest"

    amounts = sorted(t.amount for t in await _account_txns(db_session, acct.id))
    assert amounts == [Decimal("-2000"), Decimal("5000")]  # sell-to-cover, income

    row = await _latest_audit_row(db_session, "equity.vesting_recorded")
    assert row is not None
    assert row.entity_id == event.id


async def test_capital_call_increments_called_and_audit_excludes_fund_name(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    nav = await _account(db_session, household.id, "private_fund")
    funding = await _account(db_session, household.id, "checking")
    commitment = CapitalCommitment(
        household_id=household.id,
        fund_name_enc=encrypt("Meridian Growth Fund III"),
        committed_amount=Decimal("2000000"),
        called_to_date=Decimal("1000000"),
        nav_account_id=nav.id,
        vintage_year=2021,
        created_at=_now(),
    )
    db_session.add(commitment)
    await db_session.flush()

    service = PrivateFundService(db_session)
    result = await service.record_capital_call(
        primary_ctx,
        CapitalCallInput(
            capital_commitment_id=commitment.id,
            funding_account_id=funding.id,
            call_amount=Decimal("150000"),
            call_date=date(2024, 3, 1),
        ),
    )

    assert result.called_to_date == Decimal("1150000")

    txns = await _account_txns(db_session, funding.id)
    assert len(txns) == 1
    assert txns[0].amount == Decimal("-150000")
    assert txns[0].is_transfer is True

    row = await _latest_audit_row(db_session, "private_fund.capital_call")
    assert row is not None
    for field in AUDIT_EXCLUDED_FIELDS:
        assert field not in (row.previous_value or {})
        assert field not in (row.new_value or {})
    assert "fund_name_enc" not in (row.new_value or {})


async def test_sbloc_draw_posts_negative_transfer(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    sbloc = await _account(db_session, household.id, "sbloc")

    service = CreditLineService(db_session)
    txn = await service.record_sbloc_draw(
        primary_ctx,
        SblocPostingInput(
            account_id=sbloc.id,
            amount=Decimal("520000"),
            posting_date=date(2024, 6, 1),
        ),
    )

    assert txn.amount == Decimal("-520000")
    assert txn.is_transfer is True
    assert "sbloc_draw" in txn.tags

    row = await _latest_audit_row(db_session, "credit_line.sbloc_draw")
    assert row is not None
    assert row.entity_id == txn.id
