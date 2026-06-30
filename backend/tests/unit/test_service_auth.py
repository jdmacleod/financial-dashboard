import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import HTTPException
from freezegun import freeze_time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.models.audit_log import AuditLog
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.services.auth import AuthService


async def _latest_audit_action(db_session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    rows = (
        (
            await db_session.execute(
                select(AuditLog.action)
                .where(AuditLog.user_id == user_id)
                .order_by(AuditLog.id.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def test_login_success_returns_tokens_and_writes_audit_event(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    access, refresh, _must_change = await service.login(
        primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1"
    )
    assert decode_token(access, "access")["sub"] == str(primary_user.id)
    assert decode_token(refresh, "refresh")["sub"] == str(primary_user.id)
    assert "auth.login_success" in await _latest_audit_action(db_session, primary_user.id)

    await db_session.refresh(primary_user)
    assert primary_user.refresh_token_hash is not None
    assert primary_user.failed_login_attempts == 0


async def test_login_wrong_password_increments_failed_attempts_and_audits(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.login(primary_user.email, "wrong-password", ip_address="10.0.0.1")
    assert exc_info.value.status_code == 401

    await db_session.refresh(primary_user)
    assert primary_user.failed_login_attempts == 1
    assert "auth.login_failed" in await _latest_audit_action(db_session, primary_user.id)


async def test_login_unknown_email_returns_401_without_crash(db_session: AsyncSession) -> None:
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.login("nobody@example.com", "whatever", ip_address="10.0.0.1")
    assert exc_info.value.status_code == 401


async def test_login_locks_account_after_max_attempts(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    for _ in range(settings.max_login_attempts):
        with pytest.raises(HTTPException):
            await service.login(primary_user.email, "wrong-password", ip_address="10.0.0.1")

    await db_session.refresh(primary_user)
    assert primary_user.locked_until is not None
    assert "auth.account_locked" in await _latest_audit_action(db_session, primary_user.id)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1")
    assert exc_info.value.status_code == 423


async def test_login_succeeds_again_after_lockout_expires(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with freeze_time(datetime.now(UTC)) as frozen:
        for _ in range(settings.max_login_attempts):
            with pytest.raises(HTTPException):
                await service.login(primary_user.email, "wrong-password", ip_address="10.0.0.1")

        frozen.tick(timedelta(minutes=settings.lockout_minutes + 1))
        access, _refresh, _must_change = await service.login(
            primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1"
        )
        assert decode_token(access, "access")["sub"] == str(primary_user.id)


async def test_refresh_rotates_tokens(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with freeze_time(datetime.now(UTC)) as frozen:
        _, refresh_token, _must_change = await service.login(
            primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1"
        )
        frozen.tick(timedelta(seconds=1))
        new_access, new_refresh = await service.refresh(refresh_token)
    assert decode_token(new_access, "access")["sub"] == str(primary_user.id)
    assert decode_token(new_refresh, "refresh")["sub"] == str(primary_user.id)
    assert new_refresh != refresh_token


async def test_refresh_rejects_access_type_token(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    access_token = create_access_token(str(primary_user.id), str(primary_member.id), "primary")
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(access_token)
    assert exc_info.value.status_code == 401


async def test_refresh_rejects_token_not_matching_stored_hash(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with freeze_time(datetime.now(UTC)) as frozen:
        await service.login(primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1")
        frozen.tick(timedelta(seconds=1))
        stale_refresh_token = create_refresh_token(str(primary_user.id))
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(stale_refresh_token)
    assert exc_info.value.status_code == 401


async def test_logout_clears_refresh_token_hash_and_audits(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    await service.login(primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1")
    await service.logout(primary_user.id, household.id, ip_address="10.0.0.1")

    await db_session.refresh(primary_user)
    assert primary_user.refresh_token_hash is None
    assert "auth.logout" in await _latest_audit_action(db_session, primary_user.id)


async def test_reauth_success_returns_token_and_audits(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    token = await service.reauth(
        primary_user.id, "CorrectHorse123!", household.id, ip_address="10.0.0.1"
    )
    assert decode_token(token, "reauth")["sub"] == str(primary_user.id)
    assert "auth.executor_reauth_success" in await _latest_audit_action(db_session, primary_user.id)


async def test_reauth_wrong_password_rejected(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.reauth(primary_user.id, "wrong-password", household.id, ip_address="10.0.0.1")
    assert exc_info.value.status_code == 401


async def test_change_password_updates_hash_and_invalidates_sessions(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    await service.login(primary_user.email, "CorrectHorse123!", ip_address="10.0.0.1")
    await service.change_password(
        primary_user.id,
        "CorrectHorse123!",
        "NewPassword456!",
        household.id,
        ip_address="10.0.0.1",
    )

    await db_session.refresh(primary_user)
    assert primary_user.refresh_token_hash is None
    assert "auth.password_changed" in await _latest_audit_action(db_session, primary_user.id)

    new_service = AuthService(db_session)
    access, _, _must_change = await new_service.login(
        primary_user.email, "NewPassword456!", ip_address="10.0.0.1"
    )
    assert decode_token(access, "access")["sub"] == str(primary_user.id)


async def test_change_password_wrong_current_password_rejected(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.change_password(
            primary_user.id,
            "wrong-password",
            "NewPassword456!",
            household.id,
            ip_address="10.0.0.1",
        )
    assert exc_info.value.status_code == 401


async def test_admin_reset_password_resets_established_user_and_clears_lockout(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # An established user (must_change_password defaults False) who is locked out
    # with an active session — the recovery case the CLI exists for.
    primary_user.failed_login_attempts = 3
    primary_user.locked_until = datetime.now(UTC) + timedelta(minutes=10)
    primary_user.refresh_token_hash = "stale-session-hash"  # noqa: S105 — test fixture, not a secret
    await db_session.flush()

    service = AuthService(db_session)
    temp = await service.admin_reset_password(primary_user.email)

    await db_session.refresh(primary_user)
    assert verify_password(temp, primary_user.hashed_password)
    assert primary_user.must_change_password is True  # forced rotation on next login
    assert primary_user.refresh_token_hash is None  # sessions killed
    assert primary_user.failed_login_attempts == 0
    assert primary_user.locked_until is None  # lockout cleared
    assert "auth.password_reset_admin" in await _latest_audit_action(db_session, primary_user.id)


async def test_admin_reset_password_audit_row_excludes_secrets(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    service = AuthService(db_session)
    temp = await service.admin_reset_password(primary_user.email)

    rows = (
        (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.user_id == primary_user.id,
                    AuditLog.action == "auth.password_reset_admin",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    blob = f"{rows[0].previous_value}{rows[0].new_value}"
    assert temp not in blob  # plaintext never logged (CLAUDE.md rule #4)
    await db_session.refresh(primary_user)
    assert primary_user.hashed_password not in blob  # nor the hash


async def test_admin_reset_password_unknown_email_raises(
    db_session: AsyncSession,
) -> None:
    service = AuthService(db_session)
    with pytest.raises(ValueError, match="No user with email"):
        await service.admin_reset_password("nobody@example.com")


async def test_admin_reset_password_orphan_user_without_household_skips_audit(
    db_session: AsyncSession,
    make_user: Any,
) -> None:
    # A user with no linked member has no household to attribute the audit row to.
    # write_auth_event requires a household_id, so the method must skip the audit
    # write (mirroring login()) rather than crash mid-reset.
    orphan = await make_user(None, "orphan@example.com")

    service = AuthService(db_session)
    temp = await service.admin_reset_password("orphan@example.com")

    await db_session.refresh(orphan)
    assert verify_password(temp, orphan.hashed_password)
    assert orphan.must_change_password is True
    assert await _latest_audit_action(db_session, orphan.id) == []


async def test_login_after_admin_reset_forces_password_change(
    db_session: AsyncSession,
    household: Household,
    primary_member: HouseholdMember,
    primary_user: User,
) -> None:
    # End-to-end: the temp password works, and login reports must_change_password
    # so the frontend forces the user through the existing rotation flow.
    service = AuthService(db_session)
    temp = await service.admin_reset_password(primary_user.email)

    login_service = AuthService(db_session)
    access, _refresh, must_change = await login_service.login(
        primary_user.email, temp, ip_address="10.0.0.1"
    )
    assert must_change is True
    assert decode_token(access, "access")["sub"] == str(primary_user.id)
