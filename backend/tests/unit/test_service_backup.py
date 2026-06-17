"""Unit tests for BackupService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.visibility import VisibilityContext
from app.services.backup import BackupService


def _ctx(role: str = "primary", user_id: uuid.UUID | None = None) -> VisibilityContext:
    return VisibilityContext(
        household_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
        role=role,
    )


@pytest.fixture()
def session() -> AsyncMock:
    s = AsyncMock(spec=AsyncSession)
    s.add = AsyncMock()
    s.flush = AsyncMock()
    s.commit = AsyncMock()
    s.refresh = AsyncMock()
    return s


async def test_create_backup_returns_pending_job(session: AsyncMock) -> None:
    ctx = _ctx("primary")
    svc = BackupService(session)
    job = await svc.create(ctx)
    assert job.status == "pending"
    assert job.triggered_by == "manual"
    assert job.triggered_by_user_id == ctx.user_id
    session.add.assert_called_once()
    session.flush.assert_called_once()


async def test_create_backup_forbidden_for_non_primary(session: AsyncMock) -> None:
    from fastapi import HTTPException

    ctx = _ctx("partner")
    svc = BackupService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.create(ctx)
    assert exc_info.value.status_code == 403


async def test_list_backups_forbidden_for_non_primary(session: AsyncMock) -> None:
    from fastapi import HTTPException

    ctx = _ctx("partner")
    svc = BackupService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.list(ctx)
    assert exc_info.value.status_code == 403


async def test_get_backup_not_found(session: AsyncMock) -> None:
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    ctx = _ctx("primary")
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result_mock)

    svc = BackupService(session)
    with pytest.raises(HTTPException) as exc_info:
        await svc.get(ctx, uuid.uuid4())
    assert exc_info.value.status_code == 404
