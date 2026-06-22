"""Branch coverage for the demo-extension CRUD services.

The integration suite (test_write_api_demo_extension.py) exercises happy-path
create/update/delete over HTTP. These unit tests drive the service methods
directly to cover the branches HTTP round-trips miss: all-field updates,
reference-validation 400s, not-found 404s, and the `can_write` 403 guard.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.schemas.advisory_note import AdvisoryNoteCreate, AdvisoryNoteUpdate
from app.schemas.capital_commitment import CapitalCommitmentCreate, CapitalCommitmentUpdate
from app.schemas.equity_grant import EquityGrantCreate, EquityGrantUpdate
from app.schemas.insurance_policy import InsurancePolicyCreate, InsurancePolicyUpdate
from app.schemas.investment_lot import InvestmentLotCreate, InvestmentLotUpdate
from app.schemas.ownership_entity import OwnershipEntityCreate, OwnershipEntityUpdate
from app.services.advisory_note import AdvisoryNoteService
from app.services.equity_comp import EquityCompService
from app.services.insurance_policy import InsurancePolicyService
from app.services.investment_lot import InvestmentLotService
from app.services.ownership_entity import OwnershipEntityService
from app.services.private_fund import PrivateFundService


def _now() -> datetime:
    return datetime.now(UTC)


def _dep_ctx(household: Household) -> VisibilityContext:
    """A dependent context — `can_write` is False, so writes must 403."""
    return VisibilityContext(
        user_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        role="dependent",
        household_id=household.id,
    )


async def _account(
    session: AsyncSession, household: Household, account_type: str = "investment_brokerage"
) -> Account:
    acct = Account(
        household_id=household.id,
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


# --- ownership entities ------------------------------------------------------


async def test_ownership_entity_full_lifecycle(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
    primary_member: HouseholdMember,
) -> None:
    svc = OwnershipEntityService(db_session)
    entity = await svc.create(
        primary_ctx,
        OwnershipEntityCreate(
            entity_type="revocable_trust",
            name="Trust A",
            grantor_member_id=primary_member.id,
            is_in_taxable_estate=True,
            counts_in_personal_net_worth=True,
        ),
    )
    # Update every field.
    updated = await svc.update(
        primary_ctx,
        entity.id,
        OwnershipEntityUpdate(
            entity_type="ilit",
            name="Trust B",
            grantor_member_id=primary_member.id,
            is_in_taxable_estate=False,
            counts_in_personal_net_worth=False,
        ),
    )
    assert svc.to_response(updated).name == "Trust B"
    assert updated.entity_type == "ilit"
    assert updated.is_in_taxable_estate is False

    await svc.delete(primary_ctx, entity.id)
    with pytest.raises(HTTPException) as exc:
        await svc.get_by_id(primary_ctx, entity.id)
    assert exc.value.status_code == 404


async def test_ownership_entity_bad_grantor_400(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = OwnershipEntityService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            primary_ctx,
            OwnershipEntityCreate(entity_type="llc", name="X", grantor_member_id=uuid.uuid4()),
        )
    assert exc.value.status_code == 400


async def test_ownership_entity_write_requires_can_write(
    db_session: AsyncSession, household: Household
) -> None:
    svc = OwnershipEntityService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(_dep_ctx(household), OwnershipEntityCreate(entity_type="ilit", name="No"))
    assert exc.value.status_code == 403


# --- advisory notes ----------------------------------------------------------


async def test_advisory_note_full_lifecycle(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
) -> None:
    acct = await _account(db_session, household)
    svc = OwnershipEntityService(db_session)
    entity = await svc.create(
        primary_ctx, OwnershipEntityCreate(entity_type="revocable_trust", name="T")
    )
    notes = AdvisoryNoteService(db_session)

    note = await notes.create(
        primary_ctx,
        AdvisoryNoteCreate(category="estate", title="A", body="b"),
    )
    updated = await notes.update(
        primary_ctx,
        note.id,
        AdvisoryNoteUpdate(
            account_id=acct.id,
            ownership_entity_id=entity.id,
            category="tax",
            title="B",
            body="b2",
        ),
    )
    assert updated.category == "tax"
    assert updated.account_id == acct.id
    assert updated.ownership_entity_id == entity.id

    await notes.delete(primary_ctx, note.id)
    with pytest.raises(HTTPException) as exc:
        await notes.get_by_id(primary_ctx, note.id)
    assert exc.value.status_code == 404


async def test_advisory_note_bad_entity_anchor_400(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = AdvisoryNoteService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            primary_ctx,
            AdvisoryNoteCreate(
                ownership_entity_id=uuid.uuid4(), category="estate", title="A", body="b"
            ),
        )
    assert exc.value.status_code == 400


async def test_advisory_note_bad_account_anchor_404(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = AdvisoryNoteService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            primary_ctx,
            AdvisoryNoteCreate(account_id=uuid.uuid4(), category="estate", title="A", body="b"),
        )
    assert exc.value.status_code == 404


async def test_advisory_note_write_requires_can_write(
    db_session: AsyncSession, household: Household
) -> None:
    svc = AdvisoryNoteService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            _dep_ctx(household), AdvisoryNoteCreate(category="estate", title="A", body="b")
        )
    assert exc.value.status_code == 403


# --- insurance policies ------------------------------------------------------


async def test_insurance_policy_full_lifecycle(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
    primary_member: HouseholdMember,
) -> None:
    acct = await _account(db_session, household, "life_insurance_cash_value")
    ent = await OwnershipEntityService(db_session).create(
        primary_ctx, OwnershipEntityCreate(entity_type="ilit", name="ILIT")
    )
    svc = InsurancePolicyService(db_session)
    policy = await svc.create(
        primary_ctx,
        InsurancePolicyCreate(
            policy_type="term_life",
            coverage_amount=Decimal("1000000"),
            premium_amount=Decimal("500"),
            premium_cadence="annual",
        ),
    )
    updated = await svc.update(
        primary_ctx,
        policy.id,
        InsurancePolicyUpdate(
            policy_type="permanent_life",
            insured_member_id=primary_member.id,
            owner_ownership_entity_id=ent.id,
            coverage_amount=Decimal("2000000"),
            premium_amount=Decimal("900"),
            premium_cadence="monthly",
            cash_value_account_id=acct.id,
            metadata={"carrier": "X"},
        ),
    )
    assert updated.policy_type == "permanent_life"
    assert updated.cash_value_account_id == acct.id
    assert updated.policy_metadata == {"carrier": "X"}

    await svc.delete(primary_ctx, policy.id)
    with pytest.raises(HTTPException) as exc:
        await svc.get_by_id(primary_ctx, policy.id)
    assert exc.value.status_code == 404


async def test_insurance_policy_bad_refs_400(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = InsurancePolicyService(db_session)
    base = {
        "policy_type": "disability",
        "coverage_amount": Decimal("1000"),
        "premium_amount": Decimal("10"),
        "premium_cadence": "monthly",
    }
    with pytest.raises(HTTPException) as exc:
        await svc.create(primary_ctx, InsurancePolicyCreate(insured_member_id=uuid.uuid4(), **base))
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            primary_ctx, InsurancePolicyCreate(owner_ownership_entity_id=uuid.uuid4(), **base)
        )
    assert exc.value.status_code == 400


async def test_insurance_policy_write_requires_can_write(
    db_session: AsyncSession, household: Household
) -> None:
    svc = InsurancePolicyService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            _dep_ctx(household),
            InsurancePolicyCreate(
                policy_type="umbrella_liability",
                coverage_amount=Decimal("1"),
                premium_amount=Decimal("1"),
                premium_cadence="annual",
            ),
        )
    assert exc.value.status_code == 403


# --- equity grants -----------------------------------------------------------


async def test_equity_grant_full_lifecycle(
    db_session: AsyncSession,
    household: Household,
    primary_ctx: VisibilityContext,
    primary_member: HouseholdMember,
) -> None:
    svc = EquityCompService(db_session)
    grant = await svc.create_grant(
        primary_ctx,
        EquityGrantCreate(
            member_id=primary_member.id,
            grant_type="iso",
            grant_date=date(2024, 1, 1),
            shares_granted=Decimal("100"),
            strike_price=Decimal("2.50"),
            ticker="ACME",
        ),
    )
    updated = await svc.update_grant(
        primary_ctx,
        grant.id,
        EquityGrantUpdate(
            grant_type="nso",
            grant_date=date(2024, 2, 1),
            shares_granted=Decimal("200"),
            strike_price=Decimal("3.00"),
            ticker="ACME2",
            vesting_schedule={"cliff_months": 6},
            espp_discount_pct=Decimal("0.15"),
            espp_lookback=True,
        ),
    )
    assert updated.grant_type == "nso"
    assert updated.ticker == "ACME2"
    resp = await svc.grant_response(primary_ctx, updated)
    assert resp.vesting_events == []

    await svc.delete_grant(primary_ctx, grant.id)
    with pytest.raises(HTTPException) as exc:
        await svc.get_grant(primary_ctx, grant.id)
    assert exc.value.status_code == 404


async def test_equity_grant_bad_member_400(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = EquityCompService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create_grant(
            primary_ctx,
            EquityGrantCreate(
                member_id=uuid.uuid4(),
                grant_type="rsu",
                grant_date=date(2024, 1, 1),
                shares_granted=Decimal("1"),
                ticker="X",
            ),
        )
    assert exc.value.status_code == 400


async def test_equity_grant_write_requires_can_write(
    db_session: AsyncSession, household: Household, primary_member: HouseholdMember
) -> None:
    svc = EquityCompService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create_grant(
            _dep_ctx(household),
            EquityGrantCreate(
                member_id=primary_member.id,
                grant_type="rsu",
                grant_date=date(2024, 1, 1),
                shares_granted=Decimal("1"),
                ticker="X",
            ),
        )
    assert exc.value.status_code == 403


# --- investment lots ---------------------------------------------------------


async def test_investment_lot_full_lifecycle(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    acct = await _account(db_session, household)
    svc = InvestmentLotService(db_session)
    lot = await svc.create(
        primary_ctx,
        InvestmentLotCreate(
            account_id=acct.id,
            ticker="ACME",
            shares=Decimal("10"),
            basis_per_share=Decimal("5"),
            acquired_date=date(2023, 1, 1),
            basis_type="purchase",
        ),
    )
    updated = await svc.update(
        primary_ctx,
        lot.id,
        InvestmentLotUpdate(
            ticker="ACME2",
            shares=Decimal("20"),
            basis_per_share=Decimal("6"),
            acquired_date=date(2023, 2, 1),
            basis_type="rsu_vest",
        ),
    )
    assert updated.ticker == "ACME2"
    assert updated.basis_type == "rsu_vest"

    await svc.delete(primary_ctx, lot.id)
    with pytest.raises(HTTPException) as exc:
        await svc.get_by_id(primary_ctx, lot.id)
    assert exc.value.status_code == 404


async def test_investment_lot_bad_account_404(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    svc = InvestmentLotService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            primary_ctx,
            InvestmentLotCreate(
                account_id=uuid.uuid4(),
                ticker="X",
                shares=Decimal("1"),
                basis_per_share=Decimal("1"),
                acquired_date=date(2023, 1, 1),
                basis_type="purchase",
            ),
        )
    assert exc.value.status_code == 404


async def test_investment_lot_write_requires_can_write(
    db_session: AsyncSession, household: Household
) -> None:
    acct = await _account(db_session, household)
    svc = InvestmentLotService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            _dep_ctx(household),
            InvestmentLotCreate(
                account_id=acct.id,
                ticker="X",
                shares=Decimal("1"),
                basis_per_share=Decimal("1"),
                acquired_date=date(2023, 1, 1),
                basis_type="purchase",
            ),
        )
    assert exc.value.status_code == 403


# --- capital commitments -----------------------------------------------------


async def test_capital_commitment_full_lifecycle(
    db_session: AsyncSession, household: Household, primary_ctx: VisibilityContext
) -> None:
    nav = await _account(db_session, household, "private_fund")
    nav2 = await _account(db_session, household, "private_fund")
    svc = PrivateFundService(db_session)
    commitment = await svc.create(
        primary_ctx,
        CapitalCommitmentCreate(
            fund_name="Fund I",
            committed_amount=Decimal("1000000"),
            nav_account_id=nav.id,
            vintage_year=2021,
        ),
    )
    updated = await svc.update(
        primary_ctx,
        commitment.id,
        CapitalCommitmentUpdate(
            fund_name="Fund II",
            committed_amount=Decimal("2000000"),
            called_to_date=Decimal("500000"),
            nav_account_id=nav2.id,
            vintage_year=2022,
        ),
    )
    assert svc.to_response(updated).fund_name == "Fund II"
    assert updated.nav_account_id == nav2.id
    assert updated.called_to_date == Decimal("500000")

    await svc.delete(primary_ctx, commitment.id)
    with pytest.raises(HTTPException) as exc:
        await svc.update(primary_ctx, commitment.id, CapitalCommitmentUpdate(vintage_year=2020))
    assert exc.value.status_code == 404


async def test_capital_commitment_write_requires_can_write(
    db_session: AsyncSession, household: Household
) -> None:
    nav = await _account(db_session, household, "private_fund")
    svc = PrivateFundService(db_session)
    with pytest.raises(HTTPException) as exc:
        await svc.create(
            _dep_ctx(household),
            CapitalCommitmentCreate(
                fund_name="No",
                committed_amount=Decimal("1"),
                nav_account_id=nav.id,
                vintage_year=2020,
            ),
        )
    assert exc.value.status_code == 403
