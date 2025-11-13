"""Arq worker entry point."""

from typing import Any, Dict

from arq import cron
from loguru import logger

from app.workers.config import WorkerSettings
from app.workers.tasks import (
    cleanup_old_downloads,
    download_imagery,
    export_dataset,
    process_imagery,
)


async def startup(ctx: Dict[str, Any]) -> None:
    """Initialize worker on startup.

    Args:
        ctx: Worker context that will be passed to all tasks
    """
    logger.info("Starting Arq worker...")
    logger.info(f"Max jobs: {WorkerSettings.max_jobs}")
    logger.info(f"Job timeout: {WorkerSettings.job_timeout}s")


async def shutdown(ctx: Dict[str, Any]) -> None:
    """Clean up on worker shutdown.

    Args:
        ctx: Worker context
    """
    logger.info("Shutting down Arq worker...")


class WorkerConfig:
    """Arq worker configuration."""

    # Functions to make available to the worker
    functions = [
        download_imagery,
        process_imagery,
        export_dataset,
        cleanup_old_downloads,
    ]

    # Cron jobs for scheduled tasks
    cron_jobs = [
        cron(
            cleanup_old_downloads,
            hour=2,  # Run at 2 AM daily
            minute=0,
            run_at_startup=False,
        ),
    ]

    # Worker settings
    redis_settings = WorkerSettings.redis_settings
    max_jobs = WorkerSettings.max_jobs
    job_timeout = WorkerSettings.job_timeout
    keep_result = WorkerSettings.keep_result
    keep_result_forever = WorkerSettings.keep_result_forever
    max_tries = WorkerSettings.max_tries
    health_check_interval = WorkerSettings.health_check_interval
    queue_read_limit = WorkerSettings.queue_read_limit
    max_burst_jobs = WorkerSettings.max_burst_jobs

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Allow custom serialization for complex objects
    job_serializer = None
    job_deserializer = None
