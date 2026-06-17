"""Tests for the PDF exporter — WeasyPrint I/O is mocked; data fetching is real."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.debt import Debt
from app.db.models.export_job import ExportJob
from app.db.models.fire import FireScenario
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.exporters import pdf_exporter


def _now() -> datetime:
    return datetime.now(UTC)


def _make_job(
    household: Household,
    user: User,
    member: HouseholdMember,
    export_type: str = "pdf_summary",
    from_date: str = "2024-01-01",
    to_date: str = "2024-12-31",
) -> ExportJob:
    is_executor = export_type.endswith("executor")
    return ExportJob(
        id=uuid.uuid4(),
        household_id=household.id,
        export_type=export_type,
        anonymized=not is_executor,
        parameters={
            "from_date": from_date,
            "to_date": to_date,
            "member_id": str(member.id),
            "role": "primary",
        },
        status="pending",
        generated_by=user.id,
        created_at=_now(),
    )


async def _seed_account(
    db_session: AsyncSession,
    household: Household,
    account_type: str = "checking",
    nickname: str = "Checking",
) -> Account:
    acct = Account(
        household_id=household.id,
        account_type=account_type,
        nickname=nickname,
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


async def _seed_category(
    db_session: AsyncSession, household: Household, name: str, is_income: bool = False
) -> Category:
    cat = Category(
        household_id=household.id,
        name=name,
        is_income=is_income,
        is_system=False,
        created_at=_now(),
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


async def _seed_transaction(
    db_session: AsyncSession,
    account: Account,
    amount: Decimal,
    txn_date: date,
    category: Category | None = None,
    is_transfer: bool = False,
) -> Transaction:
    txn = Transaction(
        account_id=account.id,
        transaction_date=txn_date,
        amount=amount,
        payee_raw="Test Payee",
        payee_normalized="Test Payee",
        tags=[],
        source="manual",
        is_transfer=is_transfer,
        category_id=category.id if category else None,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(txn)
    await db_session.flush()
    return txn


async def _seed_snapshot(
    db_session: AsyncSession, account: Account, balance: Decimal, snap_date: date
) -> AccountSnapshot:
    snap = AccountSnapshot(
        account_id=account.id,
        snapshot_date=snap_date,
        balance=balance,
        source="manual",
        created_at=_now(),
    )
    db_session.add(snap)
    await db_session.flush()
    return snap


async def test_generate_pdf_summary_empty_household(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """PDF summary with no data produces a .pdf filename (WeasyPrint mocked)."""
    job = _make_job(household, primary_user, primary_member)
    db_session.add(job)
    await db_session.flush()

    with patch.object(pdf_exporter, "_write_pdf_sync"):
        filename = await pdf_exporter.generate(job, db_session, str(tmp_path))

    assert filename.endswith(".pdf")
    assert "summary" in filename


async def test_generate_pdf_executor_report(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """Executor export generates a .pdf file with executor in filename."""
    job = _make_job(household, primary_user, primary_member, export_type="pdf_executor")
    db_session.add(job)
    await db_session.flush()

    with patch.object(pdf_exporter, "_write_pdf_sync"):
        filename = await pdf_exporter.generate(job, db_session, str(tmp_path))

    assert filename.endswith(".pdf")
    assert "executor" in filename


async def test_generate_pdf_with_accounts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """PDF generation includes account balances without error."""
    checking = await _seed_account(db_session, household, "checking", "Checking")
    await _seed_snapshot(db_session, checking, Decimal("5000"), date(2024, 12, 31))

    inv = await _seed_account(db_session, household, "investment_brokerage", "Brokerage")
    await _seed_snapshot(db_session, inv, Decimal("50000"), date(2024, 12, 31))

    job = _make_job(household, primary_user, primary_member)
    db_session.add(job)
    await db_session.flush()

    captured_html: list[str] = []

    def _capture_html(html_str: str, path: str) -> None:
        captured_html.append(html_str)

    with patch.object(pdf_exporter, "_write_pdf_sync", side_effect=_capture_html):
        await pdf_exporter.generate(job, db_session, str(tmp_path))

    assert len(captured_html) == 1
    html = captured_html[0]
    assert "Net Worth Snapshot" in html
    assert "Investment" in html


async def test_generate_pdf_executor_includes_account_directory(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """Executor PDF includes full Account Directory section."""
    await _seed_account(db_session, household, "checking", "Main Checking")

    job = _make_job(household, primary_user, primary_member, export_type="pdf_executor")
    db_session.add(job)
    await db_session.flush()

    captured_html: list[str] = []

    def _capture_html(html_str: str, path: str) -> None:
        captured_html.append(html_str)

    with patch.object(pdf_exporter, "_write_pdf_sync", side_effect=_capture_html):
        await pdf_exporter.generate(job, db_session, str(tmp_path))

    html = captured_html[0]
    assert "Account Directory" in html
    assert "Audit Summary" in html


async def test_generate_pdf_with_spending_by_category(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """PDF includes Spending by Category section when there are expense transactions."""
    checking = await _seed_account(db_session, household, "checking", "Checking")
    food = await _seed_category(db_session, household, "Food")
    await _seed_transaction(db_session, checking, Decimal("-200"), date(2024, 6, 15), category=food)

    job = _make_job(household, primary_user, primary_member)
    db_session.add(job)
    await db_session.flush()

    captured: list[str] = []

    def _capture(html_str: str, path: str) -> None:
        captured.append(html_str)

    with patch.object(pdf_exporter, "_write_pdf_sync", side_effect=_capture):
        await pdf_exporter.generate(job, db_session, str(tmp_path))

    assert "Spending by Category" in captured[0]
    assert "Food" in captured[0]


async def test_generate_pdf_executor_with_debts_and_fire(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """Executor PDF includes Debt Schedule and FIRE Scenario Snapshot sections."""
    credit = await _seed_account(db_session, household, "credit_card", "Visa")
    debt = Debt(
        account_id=credit.id,
        current_balance=Decimal("1500"),
        interest_rate=Decimal("0.22"),
        minimum_payment=Decimal("30"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(debt)

    scenario = FireScenario(
        household_id=household.id,
        name="Coast FIRE",
        target_annual_spend=Decimal("60000"),
        safe_withdrawal_rate=Decimal("0.04"),
        expected_annual_return=Decimal("0.07"),
        expected_inflation_rate=Decimal("0.03"),
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(scenario)
    await db_session.flush()

    job = _make_job(household, primary_user, primary_member, export_type="pdf_executor")
    db_session.add(job)
    await db_session.flush()

    captured: list[str] = []

    def _capture(html_str: str, path: str) -> None:
        captured.append(html_str)

    with patch.object(pdf_exporter, "_write_pdf_sync", side_effect=_capture):
        await pdf_exporter.generate(job, db_session, str(tmp_path))

    html = captured[0]
    assert "Debt Schedule" in html
    assert "FIRE Scenario Snapshot" in html
    assert "Coast FIRE" in html


async def test_generate_pdf_makedirs_creates_output_dir(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
    tmp_path: Any,
) -> None:
    """Output directory is created if it does not exist."""
    nested_dir = str(tmp_path / "nested" / "exports")

    job = _make_job(household, primary_user, primary_member)
    db_session.add(job)
    await db_session.flush()

    import os

    with patch.object(pdf_exporter, "_write_pdf_sync"):
        await pdf_exporter.generate(job, db_session, nested_dir)

    assert os.path.isdir(nested_dir)
