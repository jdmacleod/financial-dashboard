"""Phase 3 acceptance criteria, transcribed from docs/phase-3-analysis.md."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.budget import Budget
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
    *,
    include_in_net_worth: bool = True,
) -> str:
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "account_type": account_type,
            "nickname": nickname,
            "include_in_net_worth": include_in_net_worth,
        },
        headers=auth_headers(user, member, "primary"),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _seed_category(
    db_session: AsyncSession, household: Household, name: str, *, is_income: bool = False
) -> Category:
    category = Category(
        household_id=household.id,
        name=name,
        is_income=is_income,
        is_system=False,
        created_at=_now(),
    )
    db_session.add(category)
    await db_session.flush()
    return category


async def _seed_snapshot(
    db_session: AsyncSession, account_id: str, snapshot_date: str, balance: str
) -> AccountSnapshot:
    snap = AccountSnapshot(
        account_id=uuid.UUID(account_id),
        snapshot_date=date.fromisoformat(snapshot_date),
        balance=Decimal(balance),
        source="manual",
        created_at=_now(),
    )
    db_session.add(snap)
    await db_session.flush()
    return snap


async def _seed_transaction(
    db_session: AsyncSession,
    account_id: str,
    transaction_date: str,
    amount: str,
    *,
    category_id: object = None,
    is_transfer: bool = False,
    real_estate_property_id: object = None,
) -> Transaction:
    txn = Transaction(
        account_id=uuid.UUID(account_id),
        transaction_date=date.fromisoformat(transaction_date),
        amount=Decimal(amount),
        category_id=category_id,
        is_transfer=is_transfer,
        real_estate_property_id=(
            uuid.UUID(real_estate_property_id) if real_estate_property_id else None
        ),
        tags=[],
        source="manual",
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(txn)
    await db_session.flush()
    return txn


# --- AC 1: net worth report with correct asset/liability breakdown -----------


async def test_net_worth_report_breaks_down_assets_and_liabilities(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    mortgage_id = await _create_account(
        client, primary_user, primary_member, "Mortgage", "mortgage"
    )

    await _seed_snapshot(db_session, checking_id, "2025-01-31", "5000.00")
    debt = Debt(
        account_id=uuid.UUID(mortgage_id),
        original_balance=Decimal("300000"),
        current_balance=Decimal("298000"),
        interest_rate=Decimal("4.5"),
        minimum_payment=Decimal("1500"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/reports/net-worth",
        params={"from": "2025-01-01", "to": "2025-01-31"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    current = body["current"]
    assert Decimal(current["total_assets"]) == Decimal("5000.0000")
    assert Decimal(current["total_liabilities"]) == Decimal("298000")
    assert Decimal(current["net_worth"]) == Decimal("5000.0000") - Decimal("298000")
    assert Decimal(current["breakdown"]["checking_savings"]) == Decimal("5000.0000")
    assert Decimal(current["breakdown"]["mortgage"]) == -Decimal("298000")


# --- AC 7: falls back to running transaction balance with no snapshots -------


async def test_net_worth_falls_back_to_running_balance_without_snapshots(
    client: AsyncClient,
    db_session: AsyncSession,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    await _seed_transaction(db_session, checking_id, "2025-01-05", "1000.00")
    await _seed_transaction(db_session, checking_id, "2025-01-10", "-200.00")

    resp = await client.get(
        "/api/v1/reports/net-worth",
        params={"from": "2025-01-01", "to": "2025-01-31"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    current = resp.json()["current"]
    assert Decimal(current["total_assets"]) == Decimal("800.00")


# --- AC 2: transfers excluded from cash flow ----------------------------------


async def test_cash_flow_excludes_transfers(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    income_cat = await _seed_category(db_session, household, "Paycheck", is_income=True)
    expense_cat = await _seed_category(db_session, household, "Groceries")

    await _seed_transaction(
        db_session, checking_id, "2025-02-01", "3000.00", category_id=income_cat.id
    )
    await _seed_transaction(
        db_session, checking_id, "2025-02-05", "-150.00", category_id=expense_cat.id
    )
    await _seed_transaction(
        db_session,
        checking_id,
        "2025-02-10",
        "-1000.00",
        category_id=expense_cat.id,
        is_transfer=True,
    )

    resp = await client.get(
        "/api/v1/reports/cash-flow",
        params={"from": "2025-02-01", "to": "2025-02-28"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    totals = resp.json()["totals"]
    assert Decimal(totals["income"]) == Decimal("3000.00")
    assert Decimal(totals["expenses"]) == Decimal("150.00")


# --- AC 4: budget-vs-actuals uses the most recent effective budget row -------


async def test_budget_vs_actuals_uses_most_recent_effective_row(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    category = await _seed_category(db_session, household, "Groceries")

    old_budget = Budget(
        household_id=household.id,
        category_id=category.id,
        period="monthly",
        amount=Decimal("400.00"),
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 2, 28),
    )
    new_budget = Budget(
        household_id=household.id,
        category_id=category.id,
        period="monthly",
        amount=Decimal("500.00"),
        effective_from=date(2025, 3, 1),
        effective_to=None,
    )
    db_session.add_all([old_budget, new_budget])
    await db_session.flush()

    await _seed_transaction(
        db_session, checking_id, "2025-03-10", "-450.00", category_id=category.id
    )

    resp = await client.get(
        "/api/v1/reports/budget-vs-actuals", params={"month": "2025-03"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["categories"]
    assert len(items) == 1
    assert Decimal(items[0]["budget"]) == Decimal("500.00")
    assert Decimal(items[0]["actual"]) == Decimal("450.00")


# --- AC 8: budget alerts surface categories > 90% used ------------------------


async def test_dashboard_budget_alerts_surface_categories_over_90_percent(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    category = await _seed_category(db_session, household, "Groceries")

    today = _now().date()
    month_start = today.replace(day=1)
    budget = Budget(
        household_id=household.id,
        category_id=category.id,
        period="monthly",
        amount=Decimal("100.00"),
        effective_from=month_start,
        effective_to=None,
    )
    db_session.add(budget)
    await db_session.flush()
    await _seed_transaction(
        db_session, checking_id, month_start.isoformat(), "-95.00", category_id=category.id
    )

    resp = await client.get("/api/v1/dashboard", headers=headers)
    assert resp.status_code == 200, resp.text
    alerts = resp.json()["budget_alerts"]
    assert any(a["category"] == "Groceries" for a in alerts)


# --- AC 3 & 10: property P&L with tagged income and expense transactions -----


async def test_property_pnl_computes_net_income_from_tagged_transactions(
    client: AsyncClient,
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    property_account_id = await _create_account(
        client, primary_user, primary_member, "Rental House", "real_estate"
    )
    bank_account_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )

    create_resp = await client.post(
        "/api/v1/properties",
        json={"account_id": property_account_id, "address": "123 Main St"},
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    property_id = create_resp.json()["id"]

    rent_income_cat = await _seed_category(db_session, household, "Rental Income", is_income=True)
    repairs_cat = await _seed_category(db_session, household, "Repairs")

    await _seed_transaction(
        db_session,
        bank_account_id,
        "2025-04-01",
        "1500.00",
        category_id=rent_income_cat.id,
        real_estate_property_id=property_id,
    )
    await _seed_transaction(
        db_session,
        bank_account_id,
        "2025-04-15",
        "-300.00",
        category_id=repairs_cat.id,
        real_estate_property_id=property_id,
    )

    resp = await client.get(
        "/api/v1/reports/property-pnl",
        params={"property_id": property_id, "from": "2025-04-01", "to": "2025-04-30"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert Decimal(body["gross_income"]) == Decimal("1500.00")
    assert Decimal(body["total_expenses"]) == Decimal("300.00")
    assert Decimal(body["net_income"]) == Decimal("1200.00")
    assert body["expense_breakdown"][0]["name"] == "Repairs"


# --- AC 5: audit log returns 403 for partner/dependent on the general feed ---


async def test_audit_log_general_feed_forbidden_for_non_primary(
    client: AsyncClient,
    make_member: object,
    make_user: object,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    partner = await make_member(role="partner", display_name="Partner")  # type: ignore[operator]
    partner_user = await make_user(partner, "partner@example.com")  # type: ignore[operator]

    resp = await client.get(
        "/api/v1/audit-log", headers=auth_headers(partner_user, partner, "partner")
    )
    assert resp.status_code == 403

    dependent = await make_member(role="dependent", display_name="Kid")  # type: ignore[operator]
    dependent_user = await make_user(dependent, "kid@example.com")  # type: ignore[operator]
    resp = await client.get(
        "/api/v1/audit-log", headers=auth_headers(dependent_user, dependent, "dependent")
    )
    assert resp.status_code == 403

    resp = await client.get(
        "/api/v1/audit-log", headers=auth_headers(primary_user, primary_member, "primary")
    )
    assert resp.status_code == 200


# --- AC 9: per-record history panel returns chronological events -------------


async def test_transaction_history_returns_events_oldest_first(
    client: AsyncClient,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )

    create_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/transactions",
        json={"transaction_date": "2025-05-01", "amount": "-50.00", "payee_normalized": "Store"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    txn_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/transactions/{txn_id}", json={"memo": "updated"}, headers=headers
    )
    assert update_resp.status_code == 200

    resp = await client.get(
        "/api/v1/audit-log",
        params={"entity_type": "transaction", "entity_id": txn_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) >= 2
    timestamps = [item["created_at"] for item in items]
    assert timestamps == sorted(timestamps)


async def test_transaction_history_accessible_to_non_primary_for_own_visible_account(
    client: AsyncClient,
    make_member: object,
    make_user: object,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    headers = auth_headers(primary_user, primary_member, "primary")
    checking_id = await _create_account(
        client, primary_user, primary_member, "Checking", "checking"
    )
    create_resp = await client.post(
        f"/api/v1/accounts/{checking_id}/transactions",
        json={"transaction_date": "2025-05-01", "amount": "-50.00"},
        headers=headers,
    )
    txn_id = create_resp.json()["id"]

    partner = await make_member(role="partner", display_name="Partner")  # type: ignore[operator]
    partner_user = await make_user(partner, "partner2@example.com")  # type: ignore[operator]

    resp = await client.get(
        "/api/v1/audit-log",
        params={"entity_type": "transaction", "entity_id": txn_id},
        headers=auth_headers(partner_user, partner, "partner"),
    )
    assert resp.status_code == 200
