"""Net-worth aggregation respects ownership-entity titling (spec Phase A AC #3/#4).

A revocable-trust-titled account stays in personal net worth; an ILIT/CRT-titled
account is excluded. Verified through ReportService.current_net_worth and the
FIRE input detector's net-worth computation.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.household import Household
from app.db.models.ownership_entity import OwnershipEntity
from app.db.models.snapshot import AccountSnapshot
from app.services.fire_detector import FireInputDetector
from app.services.report import ReportService


def _now() -> datetime:
    return datetime.now(UTC)


async def _entity(
    session: AsyncSession,
    household_id,
    entity_type: str,
    *,
    counts: bool,
    in_estate: bool,
) -> OwnershipEntity:
    entity = OwnershipEntity(
        household_id=household_id,
        entity_type=entity_type,
        name_enc=encrypt("Castellano Family Trust"),
        is_in_taxable_estate=in_estate,
        counts_in_personal_net_worth=counts,
        created_at=_now(),
    )
    session.add(entity)
    await session.flush()
    return entity


async def _brokerage(
    session: AsyncSession,
    household_id,
    balance: str,
    *,
    entity_id=None,
    include: bool = True,
) -> Account:
    acct = Account(
        household_id=household_id,
        account_type="investment_brokerage",
        nickname="Brokerage",
        include_in_net_worth=include,
        is_active=True,
        ownership_entity_id=entity_id,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(acct)
    await session.flush()
    session.add(
        AccountSnapshot(
            account_id=acct.id,
            snapshot_date=date(2024, 1, 1),
            balance=Decimal(balance),
            source="manual",
            created_at=_now(),
        )
    )
    await session.flush()
    return acct


async def test_ilit_excluded_revocable_included(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    revocable = await _entity(
        db_session, household.id, "revocable_trust", counts=True, in_estate=True
    )
    ilit = await _entity(db_session, household.id, "ilit", counts=False, in_estate=False)

    await _brokerage(db_session, household.id, "100000")  # untitled
    await _brokerage(db_session, household.id, "200000", entity_id=revocable.id)
    await _brokerage(db_session, household.id, "500000", entity_id=ilit.id)

    point = await ReportService(db_session).current_net_worth(primary_ctx, date(2026, 6, 1))

    # 100k untitled + 200k revocable; the 500k ILIT-titled account is excluded.
    assert point.net_worth == Decimal("300000")


async def test_include_flag_still_respected(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    await _brokerage(db_session, household.id, "100000")
    await _brokerage(db_session, household.id, "999000", include=False)

    point = await ReportService(db_session).current_net_worth(primary_ctx, date(2026, 6, 1))
    assert point.net_worth == Decimal("100000")


async def test_fire_detector_net_worth_excludes_ilit(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    ilit = await _entity(db_session, household.id, "ilit", counts=False, in_estate=False)
    await _brokerage(db_session, household.id, "100000")
    await _brokerage(db_session, household.id, "400000", entity_id=ilit.id)

    detector = FireInputDetector(db_session)
    net_worth = await detector._net_worth(primary_ctx)
    assert net_worth == Decimal("100000")
