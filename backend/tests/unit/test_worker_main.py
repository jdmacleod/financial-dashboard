"""Unit tests for ARQ worker startup / shutdown lifecycle."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


async def test_startup_sets_db_session_factory() -> None:
    """startup always sets ctx['db'] regardless of scheduler outcome."""
    ctx: dict[str, Any] = {}

    # Make arq.create_pool fail so we don't need Redis, but still hit the
    # ctx["db"] line which runs before the try block.
    with patch("arq.create_pool", new=AsyncMock(side_effect=RuntimeError("no redis"))):
        from app.worker.main import startup

        await startup(ctx)

    assert "db" in ctx


async def test_startup_scheduler_failure_is_handled_gracefully() -> None:
    """If the scheduler/ARQ setup raises, startup logs a warning and continues."""
    ctx: dict[str, Any] = {}

    with patch("arq.create_pool", new=AsyncMock(side_effect=OSError("connection refused"))):
        from app.worker.main import startup

        await startup(ctx)  # must not propagate

    assert "scheduler" not in ctx
    assert "arq_pool" not in ctx


async def test_startup_success_stores_scheduler_and_pool() -> None:
    """Full happy-path startup populates ctx with scheduler and arq_pool."""
    ctx: dict[str, Any] = {}
    mock_pool = AsyncMock()
    mock_scheduler = MagicMock()

    with (
        patch("arq.create_pool", new=AsyncMock(return_value=mock_pool)),
        patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler",
            return_value=mock_scheduler,
        ),
        patch("apscheduler.triggers.cron.CronTrigger") as mock_cron,
    ):
        mock_cron.from_crontab.return_value = MagicMock()
        from app.worker.main import startup

        await startup(ctx)

    assert ctx.get("arq_pool") is mock_pool
    assert ctx.get("scheduler") is mock_scheduler
    mock_scheduler.start.assert_called_once()


async def test_shutdown_stops_scheduler_and_closes_pool() -> None:
    """shutdown shuts down the scheduler and closes the arq pool when present."""
    mock_scheduler = MagicMock()
    mock_pool = AsyncMock()
    ctx: dict[str, Any] = {"scheduler": mock_scheduler, "arq_pool": mock_pool}

    from app.worker.main import shutdown

    await shutdown(ctx)

    mock_scheduler.shutdown.assert_called_once_with(wait=False)
    mock_pool.aclose.assert_awaited_once()


async def test_shutdown_without_scheduler_or_pool_is_safe() -> None:
    """shutdown handles an empty context without raising."""
    ctx: dict[str, Any] = {}

    from app.worker.main import shutdown

    await shutdown(ctx)  # must not raise
