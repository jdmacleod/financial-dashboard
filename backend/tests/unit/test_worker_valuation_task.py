"""Unit tests for the refresh_valuations ARQ task."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def _session_ctx(session: AsyncSession):  # type: ignore[type-arg]
    yield session


def _arq_ctx(session: AsyncSession) -> dict[str, Any]:
    return {"db": lambda: _session_ctx(session)}


async def test_refresh_valuations_skips_manual_provider() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    with patch("app.worker.tasks.valuation_tasks.settings") as mock_settings:
        mock_settings.re_valuation_provider = "manual"
        from app.worker.tasks.valuation_tasks import refresh_valuations

        await refresh_valuations(_arq_ctx(mock_session))

    # No DB queries should have been made
    mock_session.execute.assert_not_called()


async def test_refresh_valuations_skips_when_no_properties() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=result_mock)

    with patch("app.worker.tasks.valuation_tasks.settings") as mock_settings:
        mock_settings.re_valuation_provider = "attom"
        from app.worker.tasks.valuation_tasks import refresh_valuations

        await refresh_valuations(_arq_ctx(mock_session))

    mock_session.commit.assert_not_called()


async def test_refresh_valuations_logs_and_continues_on_property_error() -> None:
    from unittest.mock import MagicMock

    mock_session = AsyncMock(spec=AsyncSession)

    # One property that will fail
    fake_prop = MagicMock()
    fake_prop.id = "prop-1"
    fake_prop.address_enc = b"encrypted"

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [fake_prop]
    mock_session.execute = AsyncMock(return_value=result_mock)

    with (
        patch("app.worker.tasks.valuation_tasks.settings") as mock_settings,
        patch("app.worker.tasks.valuation_tasks.decrypt", side_effect=RuntimeError("bad")),
    ):
        mock_settings.re_valuation_provider = "attom"
        from app.worker.tasks.valuation_tasks import refresh_valuations

        await refresh_valuations(_arq_ctx(mock_session))

    # Should commit even though no valuations were created
    mock_session.commit.assert_called_once()
