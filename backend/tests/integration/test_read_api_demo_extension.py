"""Read-API endpoints for the demo-data extension tables (Option B read path).

Covers GET /advisory-notes (+ filters), /ownership-entities (name decryption),
and /insurance-policies, all household-scoped via the JWT visibility context.
"""

from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt
from app.db.models.account import Account
from app.db.models.advisory_note import AdvisoryNote
from app.db.models.capital_commitment import CapitalCommitment
from app.db.models.equity_grant import EquityGrant, VestingEvent
from app.db.models.household import Household
from app.db.models.insurance_policy import InsurancePolicy
from app.db.models.investment_lot import InvestmentLot
from app.db.models.member import HouseholdMember
from app.db.models.ownership_entity import OwnershipEntity
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def _account(db_session: AsyncSession, household: Household, account_type: str) -> Account:
    acct = Account(
        household_id=household.id,
        account_type=account_type,
        nickname=account_type,
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


async def test_list_advisory_notes_with_category_filter(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    db_session.add_all(
        [
            AdvisoryNote(
                household_id=household.id,
                category="estate",
                title="NY estate cliff",
                body="State estate exposure note.",
                created_at=_now(),
            ),
            AdvisoryNote(
                household_id=household.id,
                category="concentration",
                title="Single-stock position",
                body="Concentration note.",
                created_at=_now(),
            ),
        ]
    )
    await db_session.flush()

    headers = auth_headers(primary_user, primary_member, "primary")

    resp = await client.get("/api/v1/advisory-notes", headers=headers)
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2

    resp = await client.get("/api/v1/advisory-notes?category=estate", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["category"] == "estate"
    assert body[0]["title"] == "NY estate cliff"


async def test_list_ownership_entities_decrypts_name(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    db_session.add(
        OwnershipEntity(
            household_id=household.id,
            entity_type="ilit",
            name_enc=encrypt("Castellano Irrevocable Life Insurance Trust"),
            is_in_taxable_estate=False,
            counts_in_personal_net_worth=False,
            created_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/ownership-entities",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["name"] == "Castellano Irrevocable Life Insurance Trust"
    assert body[0]["entity_type"] == "ilit"
    assert body[0]["counts_in_personal_net_worth"] is False
    # The encrypted column must never appear in the response payload.
    assert "name_enc" not in body[0]


async def test_list_insurance_policies(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    db_session.add(
        InsurancePolicy(
            household_id=household.id,
            policy_type="umbrella_liability",
            coverage_amount=Decimal("10000000"),
            premium_amount=Decimal("2100"),
            premium_cadence="annual",
            policy_metadata={"underlying": ["auto", "home"]},
            created_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/insurance-policies",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["policy_type"] == "umbrella_liability"
    assert body[0]["coverage_amount"] == "10000000.0000"
    assert body[0]["metadata"] == {"underlying": ["auto", "home"]}


async def test_list_equity_grants_with_vesting_events(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    from datetime import date

    grant = EquityGrant(
        household_id=household.id,
        member_id=primary_member.id,
        grant_type="rsu",
        grant_date=date(2024, 1, 1),
        shares_granted=Decimal("400"),
        ticker="ACME",
        vesting_schedule={"cadence": "quarterly"},
        created_at=_now(),
    )
    db_session.add(grant)
    await db_session.flush()
    db_session.add(
        VestingEvent(
            equity_grant_id=grant.id,
            event_date=date(2024, 4, 1),
            shares_vested=Decimal("25"),
            fmv_at_event=Decimal("50"),
            taxable_ordinary_income=Decimal("1250"),
            shares_sold_to_cover=Decimal("10"),
            created_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/equity-grants",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "ACME"
    assert len(body[0]["vesting_events"]) == 1
    assert body[0]["vesting_events"][0]["taxable_ordinary_income"] == "1250.0000"


async def test_list_investment_lots_for_account(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    from datetime import date

    acct = await _account(db_session, household, "investment_brokerage")
    db_session.add(
        InvestmentLot(
            account_id=acct.id,
            ticker="NFLX",
            shares=Decimal("100"),
            basis_per_share=Decimal("330"),
            acquired_date=date(2022, 6, 15),
            basis_type="inherited_stepup",
            created_at=_now(),
        )
    )
    await db_session.flush()

    headers = auth_headers(primary_user, primary_member, "primary")
    resp = await client.get(f"/api/v1/investment-lots?account_id={acct.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ticker"] == "NFLX"
    assert body[0]["basis_type"] == "inherited_stepup"


async def test_list_capital_commitments_decrypts_fund_name(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    nav = await _account(db_session, household, "private_fund")
    db_session.add(
        CapitalCommitment(
            household_id=household.id,
            fund_name_enc=encrypt("Meridian Private Equity Fund III"),
            committed_amount=Decimal("2000000"),
            called_to_date=Decimal("1300000"),
            nav_account_id=nav.id,
            vintage_year=2021,
            created_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/capital-commitments",
        headers=auth_headers(primary_user, primary_member, "primary"),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 1
    assert body[0]["fund_name"] == "Meridian Private Equity Fund III"
    assert body[0]["called_to_date"] == "1300000.0000"
    assert "fund_name_enc" not in body[0]


async def test_endpoints_require_auth(client: AsyncClient) -> None:
    for path in (
        "/advisory-notes",
        "/ownership-entities",
        "/insurance-policies",
        "/equity-grants",
        "/investment-lots",
        "/capital-commitments",
    ):
        resp = await client.get(f"/api/v1{path}")
        assert resp.status_code in (401, 403), f"{path}: {resp.status_code}"
