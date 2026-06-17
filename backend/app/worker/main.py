from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.worker.tasks.export_tasks import run_export_job
from app.worker.tasks.import_tasks import run_import_job


async def startup(ctx: dict[str, Any]) -> None:
    ctx["db"] = AsyncSessionLocal


async def shutdown(ctx: dict[str, Any]) -> None:
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions: ClassVar[list[Any]] = [run_import_job, run_export_job]


if __name__ == "__main__":
    from arq import run_worker

    run_worker(WorkerSettings)  # type: ignore[arg-type]
