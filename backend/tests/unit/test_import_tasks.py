from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.account import Account
from app.db.models.category import Category
from app.db.models.household import Household
from app.db.models.transaction import Transaction
from app.importers.csv_importer import ParsedRow
from app.worker.tasks import import_tasks


async def _make_account(db_session: AsyncSession, household: Household, nickname: str) -> Account:
    now = datetime.now(UTC)
    account = Account(
        household_id=household.id,
        account_type="checking",
        nickname=nickname,
        include_in_net_worth=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _make_transaction(
    db_session: AsyncSession,
    account: Account,
    *,
    transaction_date: date,
    amount: Decimal,
    payee_raw: str | None = None,
    external_id: str | None = None,
    is_transfer: bool = False,
) -> Transaction:
    now = datetime.now(UTC)
    transaction = Transaction(
        account_id=account.id,
        transaction_date=transaction_date,
        amount=amount,
        payee_raw=payee_raw,
        payee_normalized=payee_raw,
        tags=[],
        source="manual",
        external_id=external_id,
        is_transfer=is_transfer,
        created_at=now,
        updated_at=now,
    )
    db_session.add(transaction)
    await db_session.flush()
    return transaction


async def test_is_duplicate_matches_on_external_id(
    db_session: AsyncSession, household: Household
) -> None:
    account = await _make_account(db_session, household, "Checking")
    await _make_transaction(
        db_session,
        account,
        transaction_date=date(2025, 1, 15),
        amount=Decimal("-10.00"),
        external_id="TXN-1",
    )
    row = ParsedRow(
        transaction_date=date(2025, 1, 15), amount=Decimal("-10.00"), external_id="TXN-1"
    )
    assert await import_tasks._is_duplicate(db_session, account.id, row) is True


async def test_is_duplicate_external_id_scoped_to_account(
    db_session: AsyncSession, household: Household
) -> None:
    account_a = await _make_account(db_session, household, "Checking")
    account_b = await _make_account(db_session, household, "Savings")
    await _make_transaction(
        db_session,
        account_a,
        transaction_date=date(2025, 1, 15),
        amount=Decimal("-10.00"),
        external_id="TXN-1",
    )
    row = ParsedRow(
        transaction_date=date(2025, 1, 15), amount=Decimal("-10.00"), external_id="TXN-1"
    )
    assert await import_tasks._is_duplicate(db_session, account_b.id, row) is False


async def test_is_duplicate_fuzzy_payee_match_without_external_id(
    db_session: AsyncSession, household: Household
) -> None:
    account = await _make_account(db_session, household, "Checking")
    await _make_transaction(
        db_session,
        account,
        transaction_date=date(2025, 1, 15),
        amount=Decimal("-84.23"),
        payee_raw="WHOLEFDS #123",
    )
    row = ParsedRow(
        transaction_date=date(2025, 1, 15), amount=Decimal("-84.23"), payee_raw="WHOLEFDS #124"
    )
    assert await import_tasks._is_duplicate(db_session, account.id, row) is True


async def test_is_duplicate_false_when_payee_dissimilar(
    db_session: AsyncSession, household: Household
) -> None:
    account = await _make_account(db_session, household, "Checking")
    await _make_transaction(
        db_session,
        account,
        transaction_date=date(2025, 1, 15),
        amount=Decimal("-84.23"),
        payee_raw="WHOLEFDS #123",
    )
    row = ParsedRow(
        transaction_date=date(2025, 1, 15),
        amount=Decimal("-84.23"),
        payee_raw="COMPLETELY DIFFERENT",
    )
    assert await import_tasks._is_duplicate(db_session, account.id, row) is False


async def test_find_transfer_candidate_matches_opposite_amount_different_account(
    db_session: AsyncSession, household: Household
) -> None:
    checking = await _make_account(db_session, household, "Checking")
    savings = await _make_account(db_session, household, "Savings")
    leg_a = await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 20), amount=Decimal("-500.00")
    )
    leg_b = await _make_transaction(
        db_session, savings, transaction_date=date(2025, 1, 21), amount=Decimal("500.00")
    )

    candidate = await import_tasks._find_transfer_candidate(db_session, household.id, leg_a)
    assert candidate is not None
    assert candidate.id == leg_b.id


async def test_find_transfer_candidate_ignores_same_account(
    db_session: AsyncSession, household: Household
) -> None:
    checking = await _make_account(db_session, household, "Checking")
    leg_a = await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 20), amount=Decimal("-500.00")
    )
    await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 21), amount=Decimal("500.00")
    )

    candidate = await import_tasks._find_transfer_candidate(db_session, household.id, leg_a)
    assert candidate is None


async def test_find_transfer_candidate_ignores_outside_window(
    db_session: AsyncSession, household: Household
) -> None:
    checking = await _make_account(db_session, household, "Checking")
    savings = await _make_account(db_session, household, "Savings")
    leg_a = await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 1), amount=Decimal("-500.00")
    )
    await _make_transaction(
        db_session, savings, transaction_date=date(2025, 1, 10), amount=Decimal("500.00")
    )

    candidate = await import_tasks._find_transfer_candidate(db_session, household.id, leg_a)
    assert candidate is None


async def test_pair_transfer_sets_shared_id_and_transfer_category(
    db_session: AsyncSession, household: Household
) -> None:
    checking = await _make_account(db_session, household, "Checking")
    savings = await _make_account(db_session, household, "Savings")
    leg_a = await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 20), amount=Decimal("-500.00")
    )
    leg_b = await _make_transaction(
        db_session, savings, transaction_date=date(2025, 1, 21), amount=Decimal("500.00")
    )
    transfer_category = Category(
        household_id=household.id,
        name="Transfer",
        is_income=False,
        is_system=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(transfer_category)
    await db_session.flush()

    await import_tasks._pair_transfer(db_session, household.id, leg_a, leg_b)

    assert leg_a.is_transfer is True
    assert leg_b.is_transfer is True
    assert leg_a.transfer_pair_id is not None
    assert leg_a.transfer_pair_id == leg_b.transfer_pair_id
    assert leg_a.category_id == transfer_category.id
    assert leg_b.category_id == transfer_category.id


async def test_pair_transfer_without_transfer_category_leaves_category_unset(
    db_session: AsyncSession, household: Household
) -> None:
    checking = await _make_account(db_session, household, "Checking")
    savings = await _make_account(db_session, household, "Savings")
    leg_a = await _make_transaction(
        db_session, checking, transaction_date=date(2025, 1, 20), amount=Decimal("-500.00")
    )
    leg_b = await _make_transaction(
        db_session, savings, transaction_date=date(2025, 1, 21), amount=Decimal("500.00")
    )

    await import_tasks._pair_transfer(db_session, household.id, leg_a, leg_b)

    assert leg_a.is_transfer is True
    assert leg_a.category_id is None


async def test_transfer_category_id_returns_none_when_absent(
    db_session: AsyncSession, household: Household
) -> None:
    assert await import_tasks._transfer_category_id(db_session, household.id) is None


async def test_transfer_category_id_ignores_non_system_category_named_transfer(
    db_session: AsyncSession, household: Household
) -> None:
    category = Category(
        household_id=household.id,
        name="Transfer",
        is_income=False,
        is_system=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(category)
    await db_session.flush()

    assert await import_tasks._transfer_category_id(db_session, household.id) is None
