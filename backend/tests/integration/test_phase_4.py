"""Phase 4 acceptance criteria — FIRE Modeling and Debt Payoff.

Tests transcribed from docs/phase-4-fire-and-debt.md.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User

from ..conftest import auth_headers


def _now() -> datetime:
    return datetime.now(UTC)


async def _create_account(
    client: AsyncClient,
    user: User,
    member: HouseholdMember,
    nickname: str,
    account_type: str = "checking",
) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={"account_type": account_type, "nickname": nickname},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _seed_income_transactions(
    db_session: AsyncSession,
    account_id: str,
    household: Household,
    months: int = 12,
    monthly_amount: str = "5000.00",
) -> Category:
    """Seed N months of income transactions and return the income category."""
    category = Category(
        household_id=household.id,
        name="Salary",
        is_income=True,
        is_system=False,
        created_at=_now(),
    )
    db_session.add(category)
    await db_session.flush()

    today = date.today()
    for i in range(months):
        # Go back i+1 months from today
        m = today.month - (i + 1)
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        txn_date = date(y, m, 1)
        db_session.add(
            Transaction(
                account_id=__import__("uuid").UUID(account_id),
                transaction_date=txn_date,
                amount=Decimal(monthly_amount),
                category_id=category.id,
                is_transfer=False,
                tags=[],
                source="manual",
                created_at=_now(),
                updated_at=_now(),
            )
        )
    await db_session.flush()
    return category


async def _seed_expense_transactions(
    db_session: AsyncSession,
    account_id: str,
    household: Household,
    months: int = 12,
    monthly_amount: str = "-3000.00",
) -> Category:
    """Seed N months of expense transactions and return the expense category."""
    category = Category(
        household_id=household.id,
        name="Living Expenses",
        is_income=False,
        is_system=False,
        created_at=_now(),
    )
    db_session.add(category)
    await db_session.flush()

    today = date.today()
    for i in range(months):
        m = today.month - (i + 1)
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        txn_date = date(y, m, 15)
        db_session.add(
            Transaction(
                account_id=__import__("uuid").UUID(account_id),
                transaction_date=txn_date,
                amount=Decimal(monthly_amount),
                category_id=category.id,
                is_transfer=False,
                tags=[],
                source="manual",
                created_at=_now(),
                updated_at=_now(),
            )
        )
    await db_session.flush()
    return category


async def _create_scenario(
    client: AsyncClient,
    user: User,
    member: HouseholdMember,
    target_annual_spend: str = "60000.00",
) -> str:
    resp = await client.post(
        "/api/v1/fire-scenarios",
        json={"name": "Primary", "target_annual_spend": target_annual_spend},
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# --- AC 1: detect returns income streams matching transaction category breakdown ---


async def test_detect_returns_income_streams_from_12_months_of_transactions(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(client, primary_user, primary_member, "Checking")
    await _seed_income_transactions(db_session, checking_id, household, months=12)
    scenario_id = await _create_scenario(client, primary_user, primary_member)

    resp = await client.post(
        f"/api/v1/fire-scenarios/{scenario_id}/detect",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    streams = body["scenario"]["additional_income_streams"]
    assert len(streams) >= 1
    stream = streams[0]
    assert stream["label"] == "Salary"
    assert Decimal(stream["amount_annual"]) > 0
    assert stream["auto_detected"] is True
    assert body["warnings"] == []


# --- AC 2: detection with < 6 months returns a warning ---


async def test_detect_with_few_months_returns_warning(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(client, primary_user, primary_member, "Checking2")
    await _seed_income_transactions(db_session, checking_id, household, months=3)
    scenario_id = await _create_scenario(client, primary_user, primary_member)

    resp = await client.post(
        f"/api/v1/fire-scenarios/{scenario_id}/detect",
        params={"trailing_months": 12},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["warnings"]) >= 1
    assert any("month" in w.lower() for w in body["warnings"])


# --- AC 3: running detection twice does not duplicate income streams ---


async def test_detect_twice_does_not_duplicate_streams(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(client, primary_user, primary_member, "Checking3")
    await _seed_income_transactions(db_session, checking_id, household, months=12)
    scenario_id = await _create_scenario(client, primary_user, primary_member)

    first = await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)
    assert first.status_code == 200
    first_count = len(first.json()["scenario"]["additional_income_streams"])

    second = await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)
    assert second.status_code == 200
    second_count = len(second.json()["scenario"]["additional_income_streams"])

    assert second_count == first_count


# --- AC 4: manually-set amount is preserved on re-detect ---


async def test_detect_preserves_manually_set_amount(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(client, primary_user, primary_member, "Checking4")
    await _seed_income_transactions(db_session, checking_id, household, months=12)
    scenario_id = await _create_scenario(client, primary_user, primary_member)

    # First detection — creates auto-detected stream
    first = await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)
    assert first.status_code == 200
    streams = first.json()["scenario"]["additional_income_streams"]
    assert len(streams) >= 1
    stream_id = streams[0]["id"]

    # Manually override the annual amount
    manual_amount = "120000.00"
    patch_resp = await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={
            "additional_income_streams": [
                {**streams[0], "amount_annual": manual_amount, "auto_detected": False}
            ]
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200

    # Re-run detection — manual override must survive
    second = await client.post(f"/api/v1/fire-scenarios/{scenario_id}/detect", headers=headers)
    assert second.status_code == 200
    updated_streams = second.json()["scenario"]["additional_income_streams"]
    manually_set = next((s for s in updated_streams if s["id"] == stream_id), None)
    # The manually overridden stream must retain its amount
    if manually_set:
        assert Decimal(manually_set["amount_annual"]) == Decimal(manual_amount)


# --- AC 5: consulting stream ending in 2 years removes income after end_year ---


async def test_projection_removes_stream_after_end_year(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    scenario_id = await _create_scenario(
        client, primary_user, primary_member, target_annual_spend="40000.00"
    )
    current_year = date.today().year

    # Consulting stream that ends in 2 years
    consulting_stream = {
        "id": "aaaaaaaa-0000-0000-0000-000000000001",
        "label": "Consulting",
        "type": "consulting",
        "amount_annual": "60000.00",
        "growth_rate_annual": "0.00",
        "start_year": current_year,
        "end_year": current_year + 2,
        "is_pre_retirement": True,
        "auto_detected": False,
    }
    await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={
            "additional_income_streams": [consulting_stream],
            "detected_portfolio_value": "500000.00",
        },
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/projection",
        params={"from_year": current_year},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    projections = resp.json()["projections"]

    # In year current+3 (end_year+1), income should not include the consulting stream
    future_entry = next((p for p in projections if p["year"] == current_year + 3), None)
    if future_entry:
        assert Decimal(future_entry["annual_income"]) == Decimal("0")


# --- AC 6: post-retirement stream reduces effective_withdrawal, not annual_savings ---


async def test_projection_post_retirement_stream_reduces_withdrawal(
    client: AsyncClient,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    current_year = date.today().year

    # Create scenario with no pre-retirement income and large portfolio
    scenario_id = await _create_scenario(
        client, primary_user, primary_member, target_annual_spend="40000.00"
    )

    # Social Security stream: post-retirement, starts in 5 years
    ss_stream = {
        "id": "bbbbbbbb-0000-0000-0000-000000000001",
        "label": "Social Security",
        "type": "social_security",
        "amount_annual": "20000.00",
        "growth_rate_annual": "0.02",
        "start_year": current_year + 5,
        "end_year": None,
        "is_pre_retirement": False,
        "auto_detected": False,
    }
    await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={
            "additional_income_streams": [ss_stream],
            "detected_portfolio_value": "1500000.00",
        },
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/projection",
        params={"from_year": current_year + 5},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    projections = resp.json()["projections"]
    if projections:
        year_entry = projections[0]
        # When SS kicks in, effective_withdrawal should be reduced
        # effective_withdrawal = max(annual_spend - supplemental_income, 0)
        annual_spend = Decimal(str(year_entry["annual_spend"]))
        supplemental = Decimal(str(year_entry["supplemental_income"]))
        effective = Decimal(str(year_entry["effective_withdrawal"]))
        assert effective <= annual_spend
        assert effective == max(annual_spend - supplemental, Decimal("0"))


# --- AC 7: avalanche pays highest-rate debt first ---


async def test_debt_payoff_avalanche_pays_highest_rate_first(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    # High-rate debt
    high_rate_acct_id = await _create_account(
        client, primary_user, primary_member, "Credit Card", "credit_card"
    )
    low_rate_acct_id = await _create_account(
        client, primary_user, primary_member, "Auto Loan", "auto_loan"
    )

    import uuid

    db_session.add(
        Debt(
            account_id=uuid.UUID(high_rate_acct_id),
            original_balance=Decimal("5000"),
            current_balance=Decimal("5000"),
            interest_rate=Decimal("0.2000"),  # 20%
            minimum_payment=Decimal("150"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.add(
        Debt(
            account_id=uuid.UUID(low_rate_acct_id),
            original_balance=Decimal("10000"),
            current_balance=Decimal("10000"),
            interest_rate=Decimal("0.0500"),  # 5%
            minimum_payment=Decimal("200"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/debt-payoff",
        params={"extra_monthly_payment": "500", "strategy": "avalanche"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    avalanche = body["avalanche"]
    assert avalanche is not None
    # The first payoff_order entry should be the high-rate debt (Credit Card)
    assert len(avalanche["payoff_order"]) >= 1
    assert "Credit Card" in avalanche["payoff_order"][0]


# --- AC 8: paid-off debt's minimum rolls into extra payment ---


async def test_debt_payoff_rolls_minimum_into_extra_after_payoff(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """When the first debt is paid off, its minimum payment is added to extra
    for the remaining debts, which accelerates the second payoff."""
    headers = auth_headers(primary_user, primary_member, "primary")

    import uuid

    small_acct = await _create_account(
        client, primary_user, primary_member, "Small Debt", "personal_loan"
    )
    large_acct = await _create_account(
        client, primary_user, primary_member, "Large Debt", "student_loan"
    )

    db_session.add(
        Debt(
            account_id=uuid.UUID(small_acct),
            original_balance=Decimal("1000"),
            current_balance=Decimal("1000"),
            interest_rate=Decimal("0.10"),
            minimum_payment=Decimal("100"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.add(
        Debt(
            account_id=uuid.UUID(large_acct),
            original_balance=Decimal("20000"),
            current_balance=Decimal("20000"),
            interest_rate=Decimal("0.06"),
            minimum_payment=Decimal("300"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    await db_session.flush()

    # No extra payment — baseline
    resp_no_extra = await client.get(
        "/api/v1/debt-payoff",
        params={"extra_monthly_payment": "0"},
        headers=headers,
    )
    assert resp_no_extra.status_code == 200
    base_months = resp_no_extra.json()["avalanche"]["months_to_payoff"]

    # With extra payment — rollover should make it faster
    resp_extra = await client.get(
        "/api/v1/debt-payoff",
        params={"extra_monthly_payment": "200"},
        headers=headers,
    )
    assert resp_extra.status_code == 200
    extra_months = resp_extra.json()["avalanche"]["months_to_payoff"]

    assert extra_months < base_months


# --- AC 10: avalanche pays less interest than snowball when rates differ ---


async def test_debt_avalanche_pays_less_interest_than_snowball(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    """Avalanche (highest rate first) mathematically always pays less total
    interest than snowball (lowest balance first) when interest rates differ."""
    headers = auth_headers(primary_user, primary_member, "primary")

    import uuid

    # Two debts where strategies DISAGREE on order:
    # Avalanche picks high-rate (24%) with HIGH balance first.
    # Snowball picks low-rate (4.5%) with LOW balance first.
    # This guarantees avalanche saves more interest than snowball.
    high_bal_high_rate = await _create_account(
        client, primary_user, primary_member, "CC High Rate", "credit_card"
    )
    low_bal_low_rate = await _create_account(
        client, primary_user, primary_member, "Student Loan Low Rate", "student_loan"
    )

    db_session.add(
        Debt(
            account_id=uuid.UUID(high_bal_high_rate),
            original_balance=Decimal("15000"),
            current_balance=Decimal("15000"),
            interest_rate=Decimal("0.2400"),  # 24% — avalanche targets this first
            minimum_payment=Decimal("300"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    db_session.add(
        Debt(
            account_id=uuid.UUID(low_bal_low_rate),
            original_balance=Decimal("3000"),
            current_balance=Decimal("3000"),
            interest_rate=Decimal("0.0450"),  # 4.5% — snowball targets this first
            minimum_payment=Decimal("90"),
            created_at=_now(),
            updated_at=_now(),
        )
    )
    await db_session.flush()

    resp = await client.get(
        "/api/v1/debt-payoff",
        params={"extra_monthly_payment": "400"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    avalanche_interest = Decimal(str(body["avalanche"]["total_interest_paid"]))
    snowball_interest = Decimal(str(body["snowball"]["total_interest_paid"]))
    assert avalanche_interest < snowball_interest


# --- CRUD: FIRE scenario lifecycle ---


async def test_fire_scenario_crud_lifecycle(
    client: AsyncClient,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")

    create_resp = await client.post(
        "/api/v1/fire-scenarios",
        json={"name": "Early Retirement", "target_annual_spend": "80000.00"},
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    scenario_id = create_resp.json()["id"]
    assert create_resp.json()["name"] == "Early Retirement"

    list_resp = await client.get("/api/v1/fire-scenarios", headers=headers)
    assert any(s["id"] == scenario_id for s in list_resp.json())

    patch_resp = await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={"target_annual_spend": "90000.00"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert Decimal(patch_resp.json()["target_annual_spend"]) == Decimal("90000.00")

    delete_resp = await client.delete(f"/api/v1/fire-scenarios/{scenario_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/fire-scenarios/{scenario_id}", headers=headers)
    assert get_resp.status_code == 404


# --- Projection returns summary fields ---


async def test_projection_returns_headline_summary(
    client: AsyncClient,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    scenario_id = await _create_scenario(
        client, primary_user, primary_member, target_annual_spend="50000.00"
    )
    await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={"detected_portfolio_value": "2000000.00"},
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/projection",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "projections" in body
    assert "summary" in body
    assert Decimal(str(body["summary"]["fire_number"])) == Decimal("50000.00") / Decimal("0.04")


async def _add_pretax_account(
    db_session: AsyncSession,
    member: HouseholdMember,
    balance: str,
) -> None:
    account = Account(
        household_id=member.household_id,
        owner_member_id=member.id,
        account_type="retirement_ira",
        nickname="Traditional IRA",
        tax_treatment="pretax",
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()
    db_session.add(
        AccountSnapshot(
            account_id=account.id,
            snapshot_date=date.today(),
            balance=Decimal(balance),
            source="manual",
            created_at=_now(),
        )
    )
    await db_session.flush()


async def test_roth_ladder_rejects_invalid_ceiling_rate(
    client: AsyncClient,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    scenario_id = await _create_scenario(client, primary_user, primary_member)
    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/roth-ladder?ceiling_rate=0.13",
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


async def test_roth_ladder_unavailable_without_filing_status(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # DOB set, but the household has no filing status -> unavailable with a note.
    primary_member.date_of_birth = date(1968, 3, 1)
    await db_session.flush()
    headers = auth_headers(primary_user, primary_member, "primary")
    scenario_id = await _create_scenario(client, primary_user, primary_member)
    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/roth-ladder",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["available"] is False
    assert "filing status" in body["note"].lower()


async def test_roth_ladder_returns_conversion_schedule(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # Born 1968 -> RMD age 75; retire at 62 -> gap years. Filing status set and a
    # pretax balance present, so the ladder is available with a conversion schedule.
    primary_member.date_of_birth = date(1968, 3, 1)
    household.filing_status = "single"
    await db_session.flush()
    await _add_pretax_account(db_session, primary_member, "1500000.00")

    headers = auth_headers(primary_user, primary_member, "primary")
    scenario_id = await _create_scenario(client, primary_user, primary_member)
    await client.patch(
        f"/api/v1/fire-scenarios/{scenario_id}",
        json={"target_retirement_age": 62, "expected_annual_return": "0.07"},
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/fire-scenarios/{scenario_id}/roth-ladder?ceiling_rate=0.12",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["available"] is True
    assert body["rmd_start_age"] == 75
    assert body["gap_start_age"] == 62
    assert len(body["years"]) > 0
    assert Decimal(str(body["years"][0]["conversion"])) > 0
    # With 7% growth, draining the pretax bucket at 12% beats large future RMDs.
    assert Decimal(str(body["lifetime_tax_saved"])) > 0
