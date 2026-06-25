"""Tests for the RMD engine — pure Uniform Lifetime table plus DB-backed
per-member scenarios."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.member import HouseholdMember
from app.db.models.snapshot import AccountSnapshot
from app.services.rmd import RmdService, compute_rmd, uniform_lifetime_divisor


class TestUniformLifetimeDivisor:
    def test_below_min_age_returns_none(self) -> None:
        assert uniform_lifetime_divisor(71) is None

    def test_known_values(self) -> None:
        assert uniform_lifetime_divisor(72) == Decimal("27.4")
        assert uniform_lifetime_divisor(73) == Decimal("26.5")
        assert uniform_lifetime_divisor(80) == Decimal("20.2")

    def test_above_max_age_clamps_to_final_period(self) -> None:
        assert uniform_lifetime_divisor(120) == Decimal("2.0")
        assert uniform_lifetime_divisor(130) == Decimal("2.0")


class TestComputeRmd:
    def test_rounds_to_cent(self) -> None:
        # 1,000,000 / 25.5 = 39215.686...
        assert compute_rmd(Decimal("1000000"), Decimal("25.5")) == Decimal("39215.69")


def _now() -> datetime:
    return datetime.now(UTC)


async def _pretax_account(
    db_session: AsyncSession,
    household_id: Any,
    owner_member_id: Any,
    *,
    tax_treatment: str = "pretax",
    account_type: str = "retirement_401k",
) -> Account:
    account = Account(
        household_id=household_id,
        owner_member_id=owner_member_id,
        account_type=account_type,
        nickname="Traditional 401k",
        tax_treatment=tax_treatment,
        include_in_net_worth=True,
        is_active=True,
        created_at=_now(),
        updated_at=_now(),
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def _snapshot(
    db_session: AsyncSession, account_id: Any, snapshot_date: date, balance: str
) -> None:
    db_session.add(
        AccountSnapshot(
            account_id=account_id,
            snapshot_date=snapshot_date,
            balance=Decimal(balance),
            source="manual",
            created_at=_now(),
        )
    )
    await db_session.flush()


async def test_computes_rmd_for_member_past_start_age(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = date(1950, 1, 1)  # start age 72
    await db_session.flush()
    account = await _pretax_account(db_session, household.id, primary_member.id)
    await _snapshot(db_session, account.id, date(2023, 12, 31), "1000000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    assert report.year == 2024
    assert len(report.members) == 1
    row = report.members[0]
    assert row.has_started is True
    assert row.pretax_balance == Decimal("1000000")
    assert row.balance_as_of == date(2023, 12, 31)
    assert row.divisor == Decimal("25.5")  # age 74 in 2024
    assert row.rmd_amount == Decimal("39215.69")
    assert row.note is None


async def test_member_below_start_age_has_not_started(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = date(1965, 6, 1)  # start age 75 (SECURE 2.0)
    await db_session.flush()
    account = await _pretax_account(db_session, household.id, primary_member.id)
    await _snapshot(db_session, account.id, date(2023, 12, 31), "500000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    row = report.members[0]
    assert row.has_started is False
    assert row.rmd_amount is None
    assert row.rmd_start_age == 75
    assert row.rmd_start_year == 2040  # 1965 + 75
    assert "begin in 2040" in (row.note or "")


async def test_member_without_dob_is_prompted(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = None
    await db_session.flush()
    await _pretax_account(db_session, household.id, primary_member.id)

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    row = report.members[0]
    assert row.has_started is False
    assert "date of birth" in (row.note or "").lower()


async def test_started_but_missing_year_end_balance(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = date(1950, 1, 1)
    await db_session.flush()
    account = await _pretax_account(db_session, household.id, primary_member.id)
    # Snapshot is in the WRONG year (current year, not the prior year).
    await _snapshot(db_session, account.id, date(2024, 6, 1), "800000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    row = report.members[0]
    assert row.has_started is True
    assert row.rmd_amount is None
    assert "2023 year-end balance" in (row.note or "")


async def test_roth_account_holder_is_not_listed(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = date(1950, 1, 1)
    await db_session.flush()
    account = await _pretax_account(
        db_session,
        household.id,
        primary_member.id,
        tax_treatment="roth",
        account_type="retirement_roth_ira",
    )
    await _snapshot(db_session, account.id, date(2023, 12, 31), "1000000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    # No pretax accounts -> member is not RMD-relevant and is omitted.
    assert report.members == []


async def test_sums_multiple_pretax_accounts_using_latest_prior_year_snapshot(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    """Batched read (E4): across two pretax accounts, each contributes its latest
    prior-year snapshot, the totals sum, and balance_as_of is the latest date —
    matching what the old per-account loop produced."""
    primary_member.date_of_birth = date(1950, 1, 1)  # attains 74 in 2024 -> divisor 25.5
    await db_session.flush()
    a1 = await _pretax_account(db_session, household.id, primary_member.id)
    a2 = await _pretax_account(db_session, household.id, primary_member.id)
    # a1 has two 2023 snapshots; the December one must win over the June one.
    await _snapshot(db_session, a1.id, date(2023, 6, 30), "400000")
    await _snapshot(db_session, a1.id, date(2023, 12, 31), "500000")
    await _snapshot(db_session, a2.id, date(2023, 11, 30), "300000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    row = report.members[0]
    assert row.pretax_balance == Decimal("800000")  # 500k (latest a1) + 300k a2
    assert row.balance_as_of == date(2023, 12, 31)  # latest across both accounts
    assert row.divisor == Decimal("25.5")
    assert row.rmd_amount == compute_rmd(Decimal("800000"), Decimal("25.5"))


async def test_account_without_prior_year_snapshot_excluded_from_sum(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
) -> None:
    primary_member.date_of_birth = date(1950, 1, 1)
    await db_session.flush()
    a1 = await _pretax_account(db_session, household.id, primary_member.id)
    a2 = await _pretax_account(db_session, household.id, primary_member.id)
    await _snapshot(db_session, a1.id, date(2023, 12, 31), "500000")
    await _snapshot(db_session, a2.id, date(2024, 6, 1), "999999")  # wrong year, ignored

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    row = report.members[0]
    assert row.pretax_balance == Decimal("500000")
    assert row.balance_as_of == date(2023, 12, 31)


async def test_single_batch_serves_multiple_members(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
    make_member: Any,
) -> None:
    """The one batched snapshot query keys correctly per account, so two members
    each get the RMD computed from their own account's balance."""
    primary_member.date_of_birth = date(1950, 1, 1)  # attains 74 -> divisor 25.5
    second = await make_member(role="partner", display_name="Pat")
    second.date_of_birth = date(1951, 1, 1)  # attains 73 in 2024 -> divisor 26.5
    await db_session.flush()
    a1 = await _pretax_account(db_session, household.id, primary_member.id)
    a2 = await _pretax_account(db_session, household.id, second.id)
    await _snapshot(db_session, a1.id, date(2023, 12, 31), "1000000")
    await _snapshot(db_session, a2.id, date(2023, 12, 31), "530000")

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    by_id = {m.member_id: m for m in report.members}
    assert len(by_id) == 2
    assert by_id[primary_member.id].rmd_amount == compute_rmd(Decimal("1000000"), Decimal("25.5"))
    assert by_id[second.id].rmd_amount == compute_rmd(Decimal("530000"), Decimal("26.5"))


async def test_logs_computed_rmd_line(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T12: a computed RMD is reconstructable from an info log line."""
    primary_member.date_of_birth = date(1950, 1, 1)
    await db_session.flush()
    account = await _pretax_account(db_session, household.id, primary_member.id)
    await _snapshot(db_session, account.id, date(2023, 12, 31), "1000000")

    with caplog.at_level(logging.INFO, logger="app.services.rmd"):
        await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    messages = [r.getMessage() for r in caplog.records if r.name == "app.services.rmd"]
    assert any(
        f"member={primary_member.id}" in m and "39215.69" in m and "attained age 74" in m
        for m in messages
    )


async def test_logs_zero_reason_when_missing_year_end_balance(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """T12: the silent '$0 because no prior-year balance' branch is logged."""
    primary_member.date_of_birth = date(1950, 1, 1)
    await db_session.flush()
    account = await _pretax_account(db_session, household.id, primary_member.id)
    await _snapshot(db_session, account.id, date(2024, 6, 1), "800000")  # wrong year

    with caplog.at_level(logging.INFO, logger="app.services.rmd"):
        await RmdService(db_session).required_distributions(primary_ctx, year=2024)

    messages = [r.getMessage() for r in caplog.records if r.name == "app.services.rmd"]
    assert any("$0" in m and "no 2023 year-end balance" in m for m in messages)


@pytest.mark.parametrize("dob_year,expected_start", [(1950, 72), (1955, 73), (1965, 75)])
async def test_start_age_follows_secure_2(
    db_session: AsyncSession,
    household: Any,
    primary_member: HouseholdMember,
    primary_ctx: VisibilityContext,
    dob_year: int,
    expected_start: int,
) -> None:
    primary_member.date_of_birth = date(dob_year, 1, 1)
    await db_session.flush()
    await _pretax_account(db_session, household.id, primary_member.id)

    report = await RmdService(db_session).required_distributions(primary_ctx, year=2024)
    assert report.members[0].rmd_start_age == expected_start
