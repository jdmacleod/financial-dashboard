import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.worker.tasks.backup_tasks import run_backup
from app.worker.tasks.export_tasks import run_export_job
from app.worker.tasks.import_tasks import run_import_job
from app.worker.tasks.valuation_tasks import refresh_valuations

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["db"] = AsyncSessionLocal

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from arq import create_pool

        arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            lambda: arq_pool.enqueue_job("run_backup"),
            CronTrigger.from_crontab(settings.backup_schedule),
            id="run_backup",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: arq_pool.enqueue_job("refresh_valuations"),
            CronTrigger.from_crontab(settings.re_valuation_refresh_schedule),
            id="refresh_valuations",
            replace_existing=True,
        )
        scheduler.start()
        ctx["scheduler"] = scheduler
        ctx["arq_pool"] = arq_pool
        logger.info(
            "APScheduler started — backup=%s valuation=%s",
            settings.backup_schedule,
            settings.re_valuation_refresh_schedule,
        )
    except Exception as exc:
        logger.warning("APScheduler could not start: %s", exc)


async def shutdown(ctx: dict[str, Any]) -> None:
    scheduler = ctx.get("scheduler")
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    arq_pool = ctx.get("arq_pool")
    if arq_pool is not None:
        await arq_pool.aclose()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions: ClassVar[list[Any]] = [
        run_import_job,
        run_export_job,
        run_backup,
        refresh_valuations,
    ]


if __name__ == "__main__":
    from arq import run_worker

    run_worker(WorkerSettings)  # type: ignore[arg-type]
