import contextlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import (
    AUDIT_EXCLUDED_FIELDS,
    AuditRepository,
    _diff,
    _snapshot,
    audit,
)
from app.core.visibility import VisibilityContext
from app.db.models.account import Account
from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.user import User


async def _make_account(db_session: AsyncSession, household: Household) -> Account:
    now = datetime.now(UTC)
    account = Account(
        household_id=household.id,
        account_type="checking",
        nickname="Checking",
        institution_name_enc=b"\x00" * 28,
        account_number_enc=b"\x00" * 28,
        notes_enc=b"\x00" * 28,
        include_in_net_worth=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(account)
    await db_session.flush()
    return account


async def test_snapshot_excludes_keys_entirely_not_just_nulls(
    db_session: AsyncSession, household: Household
) -> None:
    account = await _make_account(db_session, household)
    snap = _snapshot(account, exclude=AUDIT_EXCLUDED_FIELDS)
    for field in AUDIT_EXCLUDED_FIELDS:
        assert field not in snap


async def test_snapshot_of_user_excludes_auth_secrets(
    db_session: AsyncSession, primary_user: User
) -> None:
    primary_user.refresh_token_hash = "some-hash"  # noqa: S105 — test fixture value, not a real secret
    await db_session.flush()
    snap = _snapshot(primary_user, exclude=AUDIT_EXCLUDED_FIELDS)
    assert "hashed_password" not in snap
    assert "refresh_token_hash" not in snap


def test_snapshot_returns_empty_dict_for_none() -> None:
    assert _snapshot(None) == {}


def test_diff_only_returns_changed_keys() -> None:
    prev = {"a": 1, "b": 2, "c": 3}
    curr = {"a": 1, "b": 99, "c": 3}
    diff_prev, diff_curr = _diff(prev, curr)
    assert diff_prev == {"b": 2}
    assert diff_curr == {"b": 99}


def test_diff_includes_keys_only_present_on_one_side() -> None:
    prev = {"a": 1}
    curr = {"a": 1, "b": 2}
    diff_prev, diff_curr = _diff(prev, curr)
    assert diff_prev == {"b": None}
    assert diff_curr == {"b": 2}


class _ServiceUnderTest:
    """Minimal stand-in exercising the @audit decorator's contract directly."""

    def __init__(self, session: AsyncSession, household: Household) -> None:
        self.session = session
        self.household = household
        self.audit_repo = AuditRepository(session)

    @audit("widget.created", "widget")
    async def create(self, ctx: VisibilityContext) -> Account:
        return await _make_account(self.session, self.household)

    @audit("widget.failed", "widget")
    async def fails(self, ctx: VisibilityContext) -> Account:
        raise ValueError("boom")


def _ctx(household_id: uuid.UUID, user_id: uuid.UUID) -> VisibilityContext:
    return VisibilityContext(
        user_id=user_id, member_id=None, role="primary", household_id=household_id
    )


async def test_audit_decorator_writes_exactly_one_row_on_success(
    db_session: AsyncSession, household: Household, primary_user: User
) -> None:
    service = _ServiceUnderTest(db_session, household)
    ctx = _ctx(household.id, primary_user.id)
    await service.create(ctx)

    rows = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "widget.created")))
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_audit_decorator_writes_zero_rows_when_wrapped_fn_raises(
    db_session: AsyncSession, household: Household, primary_user: User
) -> None:
    service = _ServiceUnderTest(db_session, household)
    ctx = _ctx(household.id, primary_user.id)
    with contextlib.suppress(ValueError):
        await service.fails(ctx)

    rows = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "widget.failed")))
        .scalars()
        .all()
    )
    assert len(rows) == 0


async def test_audit_decorator_excludes_pii_even_with_prev_snapshot_set(
    db_session: AsyncSession, household: Household, primary_user: User
) -> None:
    """Regression test: a service that fails to pass `exclude=` when capturing
    `_prev_snapshot` would leak encrypted fields into the audit log even though
    the decorator excludes them from the *current* snapshot. This test sets
    `_prev_snapshot` correctly (mirroring services/account.py's fixed
    behavior) and asserts no excluded field appears in either side."""

    account = await _make_account(db_session, household)

    class _AccountUpdateService:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session
            self.audit_repo = AuditRepository(session)

        @audit("account.updated", "account")
        async def update(self, ctx: VisibilityContext) -> Account:
            self._prev_snapshot = _snapshot(account, exclude=AUDIT_EXCLUDED_FIELDS)
            account.nickname = "Renamed"
            await self.session.flush()
            return account

    service = _AccountUpdateService(db_session)
    ctx = _ctx(household.id, primary_user.id)
    await service.update(ctx)

    row = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "account.updated")))
        .scalars()
        .one()
    )
    for field in AUDIT_EXCLUDED_FIELDS:
        assert field not in (row.previous_value or {})
        assert field not in (row.new_value or {})
    assert row.new_value is not None
    assert row.new_value["nickname"] == "Renamed"


async def test_audit_repository_write_persists_row(
    db_session: AsyncSession, household: Household, primary_user: User
) -> None:
    repo = AuditRepository(db_session)
    ctx = _ctx(household.id, primary_user.id)
    await repo.write(ctx=ctx, action="manual.test", entity_type="widget")

    row = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "manual.test")))
        .scalars()
        .one()
    )
    assert row.household_id == household.id
    assert row.user_id == primary_user.id


async def test_audit_repository_write_auth_event_persists_row(
    db_session: AsyncSession, household: Household, primary_user: User
) -> None:
    repo = AuditRepository(db_session)
    await repo.write_auth_event(
        household_id=household.id,
        user_id=primary_user.id,
        action="auth.login_success",
        ip_address="10.0.0.1",
    )
    row = (
        (await db_session.execute(select(AuditLog).where(AuditLog.action == "auth.login_success")))
        .scalars()
        .one()
    )
    assert row.entity_type == "auth"
    assert str(row.ip_address) == "10.0.0.1"
