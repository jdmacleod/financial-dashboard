"""Smoke test for the test DB fixture pipeline — not part of the test plan tables."""

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_db_session_sees_migrated_schema(db_session: AsyncSession) -> None:
    result = await db_session.execute(text("SELECT count(*) FROM categories"))
    assert result.scalar_one() > 0


async def test_client_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
