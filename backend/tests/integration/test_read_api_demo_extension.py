"""Read-API endpoints for the demo-data extension tables (Option B read path).

Covers GET /advisory-notes (+ filters), /ownership-entities (name decryption),
and /insurance-policies, all household-scoped via the JWT visibility context.
"""

from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt
from app.db.models.advisory_note import AdvisoryNote
from app.db.models.household import Household
from app.db.models.insurance_policy import InsurancePolicy
from app.db.models.member import HouseholdMember
from app.db.models.ownership_entity import OwnershipEntity
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


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


async def test_endpoints_require_auth(client: AsyncClient) -> None:
    for path in ("/advisory-notes", "/ownership-entities", "/insurance-policies"):
        resp = await client.get(f"/api/v1{path}")
        assert resp.status_code in (401, 403), f"{path}: {resp.status_code}"
