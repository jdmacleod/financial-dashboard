"""Computed estate-exposure report (gap #5).

ReportService.estate_exposure groups holdings by titling, nets liabilities
against assets per bucket, splits the total into the taxable estate
(directly-owned + revocable trust) vs. holdings removed from the estate
(ILIT / irrevocable trust), and estimates federal exposure against the
applicable exemption (one per primary/partner member, capped at two).
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.debt import Debt
from app.db.models.household import Household
from app.db.models.ownership_entity import OwnershipEntity
from app.db.models.snapshot import AccountSnapshot
from app.services.report import (
    FEDERAL_ESTATE_EXEMPTION_PER_PERSON,
    FEDERAL_ESTATE_TAX_RATE,
    ReportService,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def _entity(
    session: AsyncSession, household_id: Any, entity_type: str, *, in_estate: bool
) -> OwnershipEntity:
    entity = OwnershipEntity(
        household_id=household_id,
        entity_type=entity_type,
        name_enc=encrypt(f"{entity_type} entity"),
        is_in_taxable_estate=in_estate,
        counts_in_personal_net_worth=in_estate,
        created_at=_now(),
    )
    session.add(entity)
    await session.flush()
    return entity


async def _brokerage(
    session: AsyncSession, household_id: Any, balance: str, *, entity_id: Any = None
) -> Account:
    acct = Account(
        household_id=household_id,
        account_type="investment_brokerage",
        nickname="Brokerage",
        include_in_net_worth=True,
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


async def _mortgage(session: AsyncSession, household_id: Any, balance: str) -> Account:
    acct = Account(
        household_id=household_id,
        account_type="mortgage",
        nickname="Mortgage",
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    session.add(acct)
    await session.flush()
    session.add(
        Debt(
            account_id=acct.id,
            original_balance=Decimal(balance),
            current_balance=Decimal(balance),
            interest_rate=Decimal("0.05"),
            minimum_payment=Decimal("0"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    await session.flush()
    return acct


async def test_estate_split_and_exposure(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    revocable = await _entity(db_session, household.id, "revocable_trust", in_estate=True)
    ilit = await _entity(db_session, household.id, "ilit", in_estate=False)

    # Push the directly-owned + revocable estate well over a single $15M exemption.
    await _brokerage(db_session, household.id, "16000000")  # directly owned
    await _brokerage(db_session, household.id, "4000000", entity_id=revocable.id)
    await _brokerage(db_session, household.id, "5000000", entity_id=ilit.id)
    await _mortgage(db_session, household.id, "1000000")  # directly owned liability

    report = await ReportService(db_session).estate_exposure(primary_ctx, date(2026, 6, 1))

    # Taxable estate: 16M owned + 4M revocable - 1M mortgage = 19M.
    assert report.gross_taxable_estate == Decimal("19000000")
    # ILIT 5M is removed from the estate.
    assert report.excluded_from_estate == Decimal("5000000")
    assert report.total_net_worth == Decimal("24000000")

    # primary_ctx creates exactly one primary member → one exemption.
    assert report.exemption_holders == 1
    assert report.applicable_exemption == FEDERAL_ESTATE_EXEMPTION_PER_PERSON
    # Overage = 19M - 15M = 4M; tax = 40% = 1.6M.
    assert report.taxable_overage == Decimal("4000000")
    assert report.estimated_federal_estate_tax == Decimal("4000000") * FEDERAL_ESTATE_TAX_RATE

    # Directly-owned bucket sorts first (entity_id is None).
    assert report.entities[0].entity_id is None
    assert report.entities[0].is_in_taxable_estate is True
    # The ILIT bucket is flagged out of the estate and names the entity.
    ilit_row = next(e for e in report.entities if e.entity_id == ilit.id)
    assert ilit_row.is_in_taxable_estate is False
    assert ilit_row.entity_type == "ilit"
    assert ilit_row.net_value == Decimal("5000000")


async def test_married_couple_gets_two_exemptions(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
    partner_member: Any,
) -> None:
    await _brokerage(db_session, household.id, "20000000")  # directly owned

    report = await ReportService(db_session).estate_exposure(primary_ctx, date(2026, 6, 1))

    # primary + partner → two exemptions (portability), $30M shielded.
    assert report.exemption_holders == 2
    assert report.applicable_exemption == FEDERAL_ESTATE_EXEMPTION_PER_PERSON * 2
    # 20M estate < 30M exemption → no exposure.
    assert report.taxable_overage == Decimal("0")
    assert report.estimated_federal_estate_tax == Decimal("0")
