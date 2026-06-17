"""Shared pytest fixtures.

Spins up a throwaway Postgres container (independent of docker-compose.yml,
which never publishes 5432 per CLAUDE.md rule #7) so that integration tests
run against real Postgres rather than a mock — this is required to verify
the `hearthledger_app` role's restricted `audit_log` grants (rule #3), which
have no SQLite or mocked-session equivalent.
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Settings() is built at import time (app/core/config.py) and requires these
# env vars to exist. There is no backend/.env locally — in Docker, Docker
# itself injects real values from the project-root .env; outside Docker
# (i.e. here), we supply harmless placeholders. The real test DB connection
# is constructed separately in the `engine` fixture below, pointed at the
# ephemeral test container, so these placeholders are never actually used
# for I/O — they only need to satisfy Pydantic validation at import time.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://placeholder/placeholder")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key-" + "0" * 48)
os.environ.setdefault("SECRET_ENCRYPTION_KEY", base64.b64encode(b"0" * 32).decode())

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.security import create_access_token, hash_password
from app.core.visibility import VisibilityContext
from app.db.base import get_session
from app.db.models.household import Household
from app.db.models.member import HouseholdMember
from app.db.models.user import User
from app.main import app
from app.worker.queue import get_arq_pool

BACKEND_DIR = Path(__file__).resolve().parent.parent
CONTAINER_NAME = "hearthledger-test-db"
DB_NAME = "hearthledger"
DB_USER = "hearthledger"
DB_PASSWORD = "test"  # noqa: S105 — ephemeral throwaway test container only
APP_ROLE = "hearthledger_app"
APP_ROLE_PASSWORD = "changeme"  # noqa: S105 — fixed value from db_init.sql, ephemeral test DB only
SYSTEM_HOUSEHOLD_ID = "00000000-0000-0000-0000-000000000000"


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)  # noqa: S603
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _wait_ready(port: int, timeout: float = 30.0) -> None:
    """Wait for Postgres to accept connections.

    The official postgres image runs a throwaway server for initdb, shuts it
    down, then starts the real one — pg_isready can report success during
    that first, doomed instance. Require two consecutive successes a beat
    apart to land after the restart, not during the brief window before it.
    """
    deadline = time.monotonic() + timeout
    consecutive = 0
    while time.monotonic() < deadline:
        result = subprocess.run(  # noqa: S603
            ["docker", "exec", CONTAINER_NAME, "pg_isready", "-U", DB_USER],  # noqa: S607
            capture_output=True,
        )
        consecutive = consecutive + 1 if result.returncode == 0 else 0
        if consecutive >= 2:
            return
        time.sleep(0.5)
    raise RuntimeError("Test Postgres container did not become ready in time")


@pytest.fixture(scope="session")
def postgres_urls() -> Iterator[dict[str, str]]:
    subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)  # noqa: S603, S607
    port = _free_port()
    _run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-e",
            f"POSTGRES_DB={DB_NAME}",
            "-e",
            f"POSTGRES_USER={DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={DB_PASSWORD}",
            "-p",
            f"127.0.0.1:{port}:5432",
            "postgres:16-alpine",
        ]
    )
    try:
        _wait_ready(port)
        db_init_sql = (BACKEND_DIR / "db_init.sql").read_text()
        _run(
            ["docker", "exec", "-i", CONTAINER_NAME, "psql", "-U", DB_USER, "-d", DB_NAME],
            input=db_init_sql,
        )
        admin_url = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@127.0.0.1:{port}/{DB_NAME}"
        _run(
            ["uv", "run", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env={**os.environ, "DATABASE_URL": admin_url},
        )
        yield {
            "admin": admin_url,
            "host": "127.0.0.1",
            "port": str(port),
            "db": DB_NAME,
        }
    finally:
        subprocess.run(["docker", "rm", "-f", CONTAINER_NAME], capture_output=True)  # noqa: S603, S607


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_urls: dict[str, str]) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(postgres_urls["admin"], poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session bound to a rolled-back outer transaction.

    Code under test (services/routers) frequently calls `session.commit()`
    directly — the nested-savepoint recipe below lets those commits land on
    a SAVEPOINT instead of the real transaction, which is rolled back here
    so every test starts from a clean slate without re-running migrations.
    """
    conn = await engine.connect()
    await conn.begin()
    nested = await conn.begin_nested()
    session = AsyncSession(bind=conn, expire_on_commit=False)

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sess: Any, transaction: Any) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = conn.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await conn.rollback()
        await conn.close()


class FakeArqPool:
    """Stand-in for the real Redis-backed ArqRedis pool in tests.

    No Redis container is stood up for tests (only Postgres — see
    docs/test-plan.md infra gaps); import tests instead invoke the ARQ
    worker task function directly to simulate the worker consuming the job.
    """

    def __init__(self) -> None:
        self.enqueued: list[tuple[Any, ...]] = []
        self._kv: dict[str, str] = {}

    async def enqueue_job(self, *args: Any, **kwargs: Any) -> None:
        self.enqueued.append(args)

    async def set(self, key: str, value: str | bytes, ex: int | None = None) -> None:
        self._kv[key] = str(value) if isinstance(value, bytes) else value

    async def get(self, key: str) -> bytes | None:
        val = self._kv.get(key)
        return val.encode() if val is not None else None


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def _override_get_arq_pool() -> FakeArqPool:
        return FakeArqPool()

    app.dependency_overrides[get_session] = _override_get_session
    app.dependency_overrides[get_arq_pool] = _override_get_arq_pool
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_arq_pool, None)


@pytest_asyncio.fixture
async def app_role_conn(postgres_urls: dict[str, str]) -> AsyncIterator[asyncpg.Connection[Any]]:
    """Raw connection authenticated as the restricted `hearthledger_app` role.

    Used only to verify CLAUDE.md rule #3 (audit_log append-only at the DB
    permission level) — separate from the SQLAlchemy session fixtures above,
    which connect as the privileged owner role to match current app config.
    """
    conn = await asyncpg.connect(
        host=postgres_urls["host"],
        port=int(postgres_urls["port"]),
        user=APP_ROLE,
        password=APP_ROLE_PASSWORD,
        database=postgres_urls["db"],
    )
    try:
        yield conn
    finally:
        await conn.close()


def now() -> datetime:
    return datetime.now(UTC)


@pytest_asyncio.fixture
async def household(db_session: AsyncSession) -> Household:
    h = Household(name="Test Household", settings={}, created_at=now())
    db_session.add(h)
    await db_session.flush()
    return h


@pytest_asyncio.fixture
def make_member(db_session: AsyncSession, household: Household) -> Any:
    async def _make(
        role: str = "partner", display_name: str = "Member", is_active: bool = True
    ) -> HouseholdMember:
        m = HouseholdMember(
            household_id=household.id,
            display_name=display_name,
            role=role,
            is_active=is_active,
            created_at=now(),
            updated_at=now(),
        )
        db_session.add(m)
        await db_session.flush()
        return m

    return _make


@pytest_asyncio.fixture
def make_user(db_session: AsyncSession) -> Any:
    async def _make(
        member: HouseholdMember | None,
        email: str,
        password: str = "CorrectHorse123!",  # noqa: S107 — fixture default, not a real credential
    ) -> User:
        u = User(
            member_id=member.id if member else None,
            email=email,
            hashed_password=hash_password(password),
            is_active=True,
            failed_login_attempts=0,
            last_password_change=now(),
            created_at=now(),
        )
        db_session.add(u)
        await db_session.flush()
        return u

    return _make


@pytest_asyncio.fixture
async def primary_member(make_member: Any) -> HouseholdMember:
    return await make_member(role="primary", display_name="Primary")


@pytest_asyncio.fixture
async def primary_user(make_user: Any, primary_member: HouseholdMember) -> User:
    return await make_user(primary_member, "primary@example.com")


@pytest.fixture
def primary_ctx(
    household: Household, primary_member: HouseholdMember, primary_user: User
) -> VisibilityContext:
    return VisibilityContext(
        user_id=primary_user.id,
        member_id=primary_member.id,
        role="primary",
        household_id=household.id,
        ip_address="127.0.0.1",
    )


def make_token(user: User, member: HouseholdMember | None, role: str) -> str:
    return create_access_token(str(user.id), str(member.id) if member else None, role)


def auth_headers(user: User, member: HouseholdMember | None, role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user, member, role)}"}
