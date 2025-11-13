"""Arq worker configuration."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import settings


class WorkerSettings:
    """Configuration for Arq workers."""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10  # Maximum number of concurrent jobs per worker
    job_timeout = 3600  # 1 hour timeout for downloads
    keep_result = 3600  # Keep job results for 1 hour
    keep_result_forever = False
    max_tries = 3  # Retry failed jobs up to 3 times
    health_check_interval = 60  # Health check every minute
    queue_read_limit = 100  # Read up to 100 jobs at once
    max_burst_jobs = 20  # Process up to 20 jobs in a burst


async def get_redis_pool() -> ArqRedis:
    """Get Redis connection pool for Arq.

    Returns:
        ArqRedis: Redis connection pool configured for Arq
    """
    return await create_pool(WorkerSettings.redis_settings)


# Job queue names for different types of tasks
class JobQueues:
    """Named queues for different job types."""

    DEFAULT = "arq:queue"
    DOWNLOADS = "arq:downloads"
    PROCESSING = "arq:processing"
    EXPORTS = "arq:exports"
