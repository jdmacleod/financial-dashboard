"""Required Minimum Distribution (RMD) engine.

Computes the IRS-required withdrawal from a member's pretax retirement balances
once they reach RMD age. The rule, per account owner:

    RMD(year) = (prior-year-end pretax balance) / Uniform-Lifetime-divisor(age)

Design decisions (from the member financial-identity-layer review):
  * RMD start age is birth-year dependent (SECURE 2.0) -> app.services.age.rmd_start_age.
  * The age driving the divisor is the age ATTAINED during the distribution year
    (age_in_year), per IRS, not the month/day current age.
  * The balance is the latest snapshot within the PRIOR calendar year; if a member
    has no such snapshot we surface a "add a year-end balance" note rather than
    guessing from a current balance.
  * Only accounts with tax_treatment == 'pretax' count. Roth and taxable never
    have RMDs; inherited IRAs (left unclassified) follow separate rules.

The Uniform Lifetime Table below is the IRS table effective for 2022+ RMDs.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.repositories.account import AccountRepository
from app.schemas.report import MemberRequiredDistribution, RequiredDistributionsReport
from app.services.age import age_in_year, current_age, rmd_start_age, year_turning_age

logger = logging.getLogger(__name__)

# IRS Uniform Lifetime Table (effective 2022+). Distribution period by the age
# the account owner attains during the distribution year. Ages 120+ share the
# final 2.0 period.
UNIFORM_LIFETIME_TABLE: dict[int, Decimal] = {
    72: Decimal("27.4"),
    73: Decimal("26.5"),
    74: Decimal("25.5"),
    75: Decimal("24.6"),
    76: Decimal("23.7"),
    77: Decimal("22.9"),
    78: Decimal("22.0"),
    79: Decimal("21.1"),
    80: Decimal("20.2"),
    81: Decimal("19.4"),
    82: Decimal("18.5"),
    83: Decimal("17.7"),
    84: Decimal("16.8"),
    85: Decimal("16.0"),
    86: Decimal("15.2"),
    87: Decimal("14.4"),
    88: Decimal("13.7"),
    89: Decimal("12.9"),
    90: Decimal("12.2"),
    91: Decimal("11.5"),
    92: Decimal("10.8"),
    93: Decimal("10.1"),
    94: Decimal("9.5"),
    95: Decimal("8.9"),
    96: Decimal("8.4"),
    97: Decimal("7.8"),
    98: Decimal("7.3"),
    99: Decimal("6.8"),
    100: Decimal("6.4"),
    101: Decimal("6.0"),
    102: Decimal("5.6"),
    103: Decimal("5.2"),
    104: Decimal("4.9"),
    105: Decimal("4.6"),
    106: Decimal("4.3"),
    107: Decimal("4.1"),
    108: Decimal("3.9"),
    109: Decimal("3.7"),
    110: Decimal("3.5"),
    111: Decimal("3.4"),
    112: Decimal("3.3"),
    113: Decimal("3.1"),
    114: Decimal("3.0"),
    115: Decimal("2.9"),
    116: Decimal("2.8"),
    117: Decimal("2.7"),
    118: Decimal("2.5"),
    119: Decimal("2.3"),
    120: Decimal("2.0"),
}

_MIN_TABLE_AGE = min(UNIFORM_LIFETIME_TABLE)
_MAX_TABLE_AGE = max(UNIFORM_LIFETIME_TABLE)


def uniform_lifetime_divisor(age: int) -> Decimal | None:
    """Distribution period for ``age``. None below the table's minimum age;
    ages above the table's maximum clamp to the final period (no crash)."""
    if age < _MIN_TABLE_AGE:
        return None
    if age >= _MAX_TABLE_AGE:
        return UNIFORM_LIFETIME_TABLE[_MAX_TABLE_AGE]
    return UNIFORM_LIFETIME_TABLE[age]


def compute_rmd(balance: Decimal, divisor: Decimal) -> Decimal:
    """RMD dollar amount, rounded to the cent."""
    return (balance / divisor).quantize(Decimal("0.01"))


class RmdService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.account_repo = AccountRepository(session)

    async def required_distributions(
        self, ctx: VisibilityContext, year: int | None = None
    ) -> RequiredDistributionsReport:
        """Per-member RMD for ``year`` (current year by default), covering every
        member who owns at least one pretax retirement account."""
        year = year or date.today().year

        accounts = await self.account_repo.get_visible(ctx, is_active=True)
        pretax_by_owner: dict[uuid.UUID, list[Account]] = defaultdict(list)
        for account in accounts:
            if account.tax_treatment == "pretax" and account.owner_member_id is not None:
                pretax_by_owner[account.owner_member_id].append(account)

        # Prior-year-end balances for every pretax account in one query (E4):
        # one keyed DISTINCT ON read instead of a per-account snapshot lookup.
        pretax_ids = [a.id for owned in pretax_by_owner.values() for a in owned]
        snapshots = await self._batch_prior_year_snapshots(pretax_ids, year - 1)

        members = await self._active_members(ctx)
        rows: list[MemberRequiredDistribution] = []
        for member in members:
            owned = pretax_by_owner.get(member.id)
            if not owned:
                continue  # not RMD-relevant — no pretax retirement accounts
            rows.append(self._member_rmd(member, owned, year, snapshots))

        return RequiredDistributionsReport(year=year, members=rows)

    def _member_rmd(
        self,
        member: HouseholdMember,
        pretax_accounts: list[Account],
        year: int,
        snapshots: dict[uuid.UUID, tuple[Decimal, date]],
    ) -> MemberRequiredDistribution:
        dob = member.date_of_birth
        start_age = rmd_start_age(dob)
        start_year = year_turning_age(dob, start_age) if start_age is not None else None

        base = MemberRequiredDistribution(
            member_id=member.id,
            display_name=member.display_name,
            date_of_birth=dob,
            current_age=current_age(dob),
            rmd_start_age=start_age,
            rmd_start_year=start_year,
            has_started=False,
            pretax_balance=None,
            balance_as_of=None,
            divisor=None,
            rmd_amount=None,
            note=None,
        )

        if dob is None or start_age is None:
            base.note = "Add a date of birth to see required distributions."
            logger.info(
                "RMD %s member=%s: $0 — no date of birth (pretax_accounts=%d)",
                year,
                member.id,
                len(pretax_accounts),
            )
            return base

        attained_age = age_in_year(dob, year)
        assert attained_age is not None  # dob is not None here
        if attained_age < start_age:
            base.note = f"RMDs begin in {start_year} (age {start_age})."
            logger.info(
                "RMD %s member=%s: $0 — age %d below start age %d (begins %s)",
                year,
                member.id,
                attained_age,
                start_age,
                start_year,
            )
            return base

        base.has_started = True
        prior_year = year - 1
        total, as_of = _sum_prior_year_balances(pretax_accounts, snapshots)
        if as_of is None:
            base.note = f"Add a {prior_year} year-end balance to compute the RMD."
            logger.info(
                "RMD %s member=%s: $0 — attained age %d but no %d year-end balance "
                "across %d pretax account(s)",
                year,
                member.id,
                attained_age,
                prior_year,
                len(pretax_accounts),
            )
            return base

        divisor = uniform_lifetime_divisor(attained_age)
        assert divisor is not None  # attained_age >= start_age >= table minimum
        base.pretax_balance = total
        base.balance_as_of = as_of
        base.divisor = divisor
        base.rmd_amount = compute_rmd(total, divisor)
        logger.info(
            "RMD %s member=%s: attained age %d, pretax base %s as of %s, divisor %s -> %s",
            year,
            member.id,
            attained_age,
            total,
            as_of,
            divisor,
            base.rmd_amount,
        )
        return base

    async def _active_members(self, ctx: VisibilityContext) -> list[HouseholdMember]:
        result = await self.session.execute(
            select(HouseholdMember).where(
                HouseholdMember.household_id == ctx.household_id,
                HouseholdMember.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def _batch_prior_year_snapshots(
        self, account_ids: list[uuid.UUID], prior_year: int
    ) -> dict[uuid.UUID, tuple[Decimal, date]]:
        """Latest within-``prior_year`` snapshot for each account, in one query.

        Postgres ``DISTINCT ON (account_id)`` with ``ORDER BY account_id,
        snapshot_date DESC`` keeps the most-recent prior-year row per account —
        the same batched-balance pattern AccountService uses (account.py). Accounts
        with no prior-year snapshot are simply absent from the map.
        """
        if not account_ids:
            return {}
        result = await self.session.execute(
            select(
                AccountSnapshot.account_id,
                AccountSnapshot.balance,
                AccountSnapshot.snapshot_date,
            )
            .where(
                AccountSnapshot.account_id.in_(account_ids),
                AccountSnapshot.snapshot_date >= date(prior_year, 1, 1),
                AccountSnapshot.snapshot_date <= date(prior_year, 12, 31),
            )
            .distinct(AccountSnapshot.account_id)
            .order_by(AccountSnapshot.account_id, AccountSnapshot.snapshot_date.desc())
        )
        return {row.account_id: (row.balance, row.snapshot_date) for row in result.all()}


def _sum_prior_year_balances(
    accounts: list[Account], snapshots: dict[uuid.UUID, tuple[Decimal, date]]
) -> tuple[Decimal, date | None]:
    """Sum the batched prior-year snapshots for ``accounts``. Returns the running
    total and the most recent snapshot date used (None when not a single account
    has a prior-year snapshot)."""
    total = Decimal("0")
    latest: date | None = None
    for account in accounts:
        snap = snapshots.get(account.id)
        if snap is not None:
            balance, snap_date = snap
            total += balance
            latest = snap_date if latest is None else max(latest, snap_date)
    return total, latest
