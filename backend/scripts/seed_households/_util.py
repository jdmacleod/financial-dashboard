"""Shared utilities for the HearthLedger demo seed script."""
from __future__ import annotations

import calendar
import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from passlib.context import CryptContext

from app.core.encryption import encrypt
from app.db.models.access_grant import AccountAccessGrant
from app.db.models.account import Account
from app.db.models.budget import Budget
from app.db.models.debt import Debt
from app.db.models.fire import FireScenario
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.property_valuation import PropertyValuation
from app.db.models.real_estate import RealEstateProperty
from app.db.models.snapshot import AccountSnapshot
from app.db.models.transaction import Transaction
from app.db.models.user import User

if TYPE_CHECKING:
    import random

    from sqlalchemy.ext.asyncio import AsyncSession

_pwd_ctx = CryptContext(schemes=["bcrypt"])
DEMO_HASH: str = _pwd_ctx.hash("HearthDemo1!")

DATE_START = date(2024, 1, 1)
DATE_END = date(2026, 6, 20)

# Investment account types (balance from snapshots)
SNAPSHOT_TYPES = frozenset({
    "investment_brokerage",
    "retirement_401k",
    "retirement_403b",
    "retirement_ira",
    "retirement_roth_ira",
    "pension",
    "hsa",
})


# ── Timing helpers ────────────────────────────────────────────────────────────

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def last_day_of(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def all_months() -> list[date]:
    """First-of-month for each month Jan 2024 – Jun 2026 inclusive."""
    months: list[date] = []
    y, m = DATE_START.year, DATE_START.month
    while (y, m) <= (DATE_END.year, DATE_END.month):
        months.append(date(y, m, 1))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return months


def clamp_day(year: int, month: int, day: int) -> date:
    """Return date(year, month, day) clamped to last valid day and to DATE_END."""
    _, max_d = calendar.monthrange(year, month)
    d = min(day, max_d)
    dt = date(year, month, d)
    return min(dt, DATE_END)


def rand_date(year: int, month: int, rng: random.Random, avoid_sunday: bool = False) -> date:
    _, max_d = calendar.monthrange(year, month)
    for _ in range(20):
        d = rng.randint(1, min(max_d, 28))
        dt = date(year, month, d)
        if dt > DATE_END:
            dt = DATE_END
        if avoid_sunday and dt.weekday() == 6:
            continue
        return dt
    return clamp_day(year, month, 15)


def friday_dates(year: int, month: int) -> list[date]:
    _, max_d = calendar.monthrange(year, month)
    return [date(year, month, d) for d in range(1, max_d + 1)
            if date(year, month, d).weekday() == 4]


def jitter(amount: Decimal, rng: random.Random, pct: float = 0.10) -> Decimal:
    f = Decimal(str(1.0 + rng.uniform(-pct, pct)))
    return (amount * f).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Row constructors ──────────────────────────────────────────────────────────

def make_household(name: str) -> Household:
    return Household(id=uuid.uuid4(), name=name, settings={}, created_at=utcnow())


def make_member(
    household_id: uuid.UUID,
    display_name: str,
    role: str,
    *,
    date_of_birth: date | None = None,
) -> HouseholdMember:
    now = utcnow()
    return HouseholdMember(
        id=uuid.uuid4(),
        household_id=household_id,
        display_name=display_name,
        role=role,
        date_of_birth=date_of_birth,
        is_active=True,
        settings={},
        created_at=now,
        updated_at=now,
    )


def make_user(member_id: uuid.UUID, email: str) -> User:
    now = utcnow()
    return User(
        id=uuid.uuid4(),
        member_id=member_id,
        email=email,
        hashed_password=DEMO_HASH,
        is_active=True,
        last_password_change=now,
        created_at=now,
    )


def make_account(
    household_id: uuid.UUID,
    account_type: str,
    nickname: str,
    institution: str,
    last4: str | None,
    *,
    owner_member_id: uuid.UUID | None = None,
    include_in_net_worth: bool = True,
) -> Account:
    now = utcnow()
    return Account(
        id=uuid.uuid4(),
        household_id=household_id,
        owner_member_id=owner_member_id,
        account_type=account_type,
        nickname=nickname,
        institution_name_enc=encrypt(institution) if institution else None,
        account_number_enc=encrypt(last4) if last4 else None,
        include_in_net_worth=include_in_net_worth,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_property(
    account_id: uuid.UUID,
    address: str,
    property_type: str,
    purchase_date: date,
    purchase_price: Decimal,
    linked_mortgage_id: uuid.UUID | None = None,
) -> RealEstateProperty:
    now = utcnow()
    return RealEstateProperty(
        id=uuid.uuid4(),
        account_id=account_id,
        address_enc=encrypt(address),
        property_type=property_type,
        purchase_date=purchase_date,
        purchase_price=purchase_price,
        linked_mortgage_account_id=linked_mortgage_id,
        created_at=now,
        updated_at=now,
    )


def make_valuation(
    property_id: uuid.UUID, val_date: date, amount: Decimal
) -> PropertyValuation:
    return PropertyValuation(
        id=uuid.uuid4(),
        real_estate_property_id=property_id,
        valuation_date=val_date,
        estimated_value=amount,
        source="manual",
        created_at=utcnow(),
    )


def make_budget(
    household_id: uuid.UUID,
    category_id: uuid.UUID,
    amount: Decimal,
    effective_from: date,
) -> Budget:
    return Budget(
        id=uuid.uuid4(),
        household_id=household_id,
        category_id=category_id,
        period="monthly",
        amount=amount,
        effective_from=effective_from,
        effective_to=None,
    )


def make_debt(
    account_id: uuid.UUID,
    original_balance: Decimal,
    current_balance: Decimal,
    interest_rate: Decimal,
    minimum_payment: Decimal,
    loan_term_months: int,
    origination_date: date,
) -> Debt:
    now = utcnow()
    return Debt(
        id=uuid.uuid4(),
        account_id=account_id,
        original_balance=original_balance,
        current_balance=current_balance,
        interest_rate=interest_rate,
        minimum_payment=minimum_payment,
        loan_term_months=loan_term_months,
        origination_date=origination_date,
        payment_due_day=15,
        created_at=now,
        updated_at=now,
    )


def make_fire_scenario(
    household_id: uuid.UUID,
    member_id: uuid.UUID | None,
    name: str,
    target_annual_spend: Decimal,
    expected_annual_return: Decimal,
    expected_inflation_rate: Decimal,
    target_retirement_age: int,
    income_streams: list[dict],
    safe_withdrawal_rate: Decimal = Decimal("0.04"),
) -> FireScenario:
    now = utcnow()
    return FireScenario(
        id=uuid.uuid4(),
        household_id=household_id,
        member_id=member_id,
        name=name,
        target_annual_spend=target_annual_spend,
        safe_withdrawal_rate=safe_withdrawal_rate,
        expected_annual_return=expected_annual_return,
        expected_inflation_rate=expected_inflation_rate,
        target_retirement_age=target_retirement_age,
        additional_income_streams=income_streams,
        detection_trailing_months=12,
        created_at=now,
        updated_at=now,
    )


def make_access_grant(
    account_id: uuid.UUID,
    owner_member_id: uuid.UUID,
    grantee_member_id: uuid.UUID,
    granted_by_user_id: uuid.UUID,
) -> AccountAccessGrant:
    return AccountAccessGrant(
        id=uuid.uuid4(),
        account_id=account_id,
        owner_member_id=owner_member_id,
        grantee_member_id=grantee_member_id,
        granted_by_user_id=granted_by_user_id,
        access_level="read",
        is_active=True,
        created_at=utcnow(),
    )


# ── Transaction helpers ───────────────────────────────────────────────────────

def tx(
    account_id: uuid.UUID,
    tx_date: date,
    amount: Decimal,
    payee: str,
    cat_id: uuid.UUID | None,
    *,
    is_transfer: bool = False,
    pair_id: uuid.UUID | None = None,
    prop_id: uuid.UUID | None = None,
    memo: str | None = None,
) -> Transaction:
    is_reviewed = tx_date < date(2026, 6, 1)
    return Transaction(
        id=uuid.uuid4(),
        account_id=account_id,
        transaction_date=tx_date,
        amount=amount,
        payee_raw=payee,
        payee_normalized=payee,
        memo=memo,
        category_id=cat_id,
        is_transfer=is_transfer,
        transfer_pair_id=pair_id,
        real_estate_property_id=prop_id,
        is_reviewed=is_reviewed,
        source="manual",
        tags=[],
        created_at=utcnow(),
        updated_at=utcnow(),
    )


def transfer(
    from_id: uuid.UUID,
    to_id: uuid.UUID,
    tx_date: date,
    amount: Decimal,
    payee: str,
    cat_id: uuid.UUID,
    *,
    prop_id: uuid.UUID | None = None,
    memo: str | None = None,
) -> tuple[Transaction, Transaction]:
    """Debit from_id, credit to_id. Returns (debit, credit)."""
    pair_id = uuid.uuid4()
    kw = dict(is_transfer=True, pair_id=pair_id, prop_id=prop_id, memo=memo)
    return (
        tx(from_id, tx_date, -amount, payee, cat_id, **kw),
        tx(to_id, tx_date, amount, payee, cat_id, **kw),
    )


def opening_balance_tx(
    account_id: uuid.UUID,
    amount: Decimal,
    cat_id: uuid.UUID | None = None,
) -> Transaction:
    """Synthetic transaction on 2023-12-31 to set the starting balance."""
    return tx(
        account_id,
        date(2023, 12, 31),
        amount,
        "Seed: Opening Balance",
        cat_id,
        memo="Auto-generated seed opening balance",
    )


def snapshot(
    account_id: uuid.UUID,
    snap_date: date,
    balance: Decimal,
) -> AccountSnapshot:
    return AccountSnapshot(
        id=uuid.uuid4(),
        account_id=account_id,
        snapshot_date=snap_date,
        balance=balance.quantize(Decimal("0.0001")),
        source="manual",
        created_at=utcnow(),
    )


def build_snapshots(
    account_id: uuid.UUID,
    start_balance: Decimal,
    monthly_contributions: dict[date, Decimal],
    annual_return: float = 0.09,
    dips: dict[date, float] | None = None,
) -> list[AccountSnapshot]:
    """Monthly snapshots from 2024-01-31 through 2026-05-31 using simple growth formula."""
    balance = start_balance
    snaps: list[AccountSnapshot] = []
    for month_start in all_months():
        if month_start >= date(2026, 6, 1):
            break
        month_end = last_day_of(month_start.year, month_start.month)
        balance = (balance * Decimal(str(1 + annual_return / 12))).quantize(Decimal("0.01"))
        balance += monthly_contributions.get(month_end, Decimal("0"))
        if dips and month_end in dips:
            balance = (balance * Decimal(str(1 + dips[month_end]))).quantize(Decimal("0.01"))
        snaps.append(snapshot(account_id, month_end, balance))
    return snaps


def gen_variable(
    account_id: uuid.UUID,
    year: int,
    month: int,
    cat_id: uuid.UUID,
    merchants: list[str],
    min_total: Decimal,
    max_total: Decimal,
    min_count: int,
    max_count: int,
    rng: random.Random,
    *,
    avoid_sunday: bool = False,
    prop_id: uuid.UUID | None = None,
) -> list[Transaction]:
    """Generate N split variable transactions for a category in a given month."""
    _, max_d = calendar.monthrange(year, month)
    total = jitter((min_total + max_total) / 2, rng, pct=0.12)
    count = rng.randint(min_count, max_count)
    if count == 0:
        return []

    # Split total into `count` amounts summing to total
    parts: list[Decimal] = []
    remaining = total
    for i in range(count - 1):
        share = jitter(total / count, rng, pct=0.20)
        share = min(share, remaining - Decimal("0.01") * (count - 1 - i))
        parts.append(share.quantize(Decimal("0.01")))
        remaining -= parts[-1]
    parts.append(remaining.quantize(Decimal("0.01")))

    txns: list[Transaction] = []
    for amt in parts:
        if amt <= Decimal("0"):
            continue
        dt = rand_date(year, month, rng, avoid_sunday=avoid_sunday)
        payee = rng.choice(merchants)
        txns.append(tx(account_id, dt, -amt, payee, cat_id, prop_id=prop_id))
    return txns
