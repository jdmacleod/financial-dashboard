"""CLAUDE.md rule #3: audit_log is append-only at the DB permission level.

The hearthledger_app role has only SELECT, INSERT on audit_log — verified
here directly against real Postgres grants, since this cannot be expressed
or verified through a mocked session.
"""

import asyncpg
import pytest


async def test_app_role_cannot_update_audit_log(app_role_conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await app_role_conn.execute("UPDATE audit_log SET action = 'x' WHERE false")


async def test_app_role_cannot_delete_from_audit_log(app_role_conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await app_role_conn.execute("DELETE FROM audit_log WHERE false")


async def test_app_role_cannot_truncate_audit_log(app_role_conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await app_role_conn.execute("TRUNCATE audit_log")


async def test_app_role_can_insert_and_select_audit_log(app_role_conn: asyncpg.Connection) -> None:  # type: ignore[type-arg]
    # Raw asyncpg autocommits each statement, so an uncommitted-looking INSERT
    # here would otherwise permanently pollute the shared test DB for the
    # rest of the pytest session (it broke SetupService.is_setup_done() for
    # every later test until wrapped in a transaction that rolls back).
    tx = app_role_conn.transaction()
    await tx.start()
    try:
        household_id = await app_role_conn.fetchval(
            "INSERT INTO households (id, name, settings, created_at) "
            "VALUES (gen_random_uuid(), 'Perm Test Household', '{}', now()) RETURNING id"
        )
        await app_role_conn.execute(
            """
            INSERT INTO audit_log (id, household_id, action, entity_type)
            VALUES (gen_random_uuid(), $1, 'test.action', 'test')
            """,
            household_id,
        )
        rows = await app_role_conn.fetch("SELECT * FROM audit_log WHERE action = 'test.action'")
        assert len(rows) == 1
    finally:
        await tx.rollback()
