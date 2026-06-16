from arq.connections import RedisSettings

from app.core.config import settings
from app.db.base import AsyncSessionLocal


async def startup(ctx):
    ctx["db"] = AsyncSessionLocal


async def shutdown(ctx):
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions = []  # tasks registered per phase


if __name__ == "__main__":
    from arq import run_worker

    run_worker(WorkerSettings)
