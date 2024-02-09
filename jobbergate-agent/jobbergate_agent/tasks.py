"""Task definitions for the Jobbergate Agent."""

import asyncio
from typing import Union, Callable, Awaitable, Any, List, Dict

from buzz import handle_errors
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.jobbergate.submit import submit_pending_jobs
from jobbergate_agent.jobbergate.update import update_active_jobs
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import log_error, logger_wraps
from jobbergate_agent.utils.scheduler import BaseScheduler, Job


async def not_implemented():
    raise NotImplementedError("A task class must override the BaseTask's function property")


class BaseTask:
    function: Callable[[], Awaitable[None]] = not_implemented
    enabled: bool = True
    priority: int = 0
    scheduler_kwargs: Dict[str, Any] = dict(
        trigger="interval",
        seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS,
    )


class UpdateSubmissionsTask(BaseTask):
    function = update_active_jobs


class PendingSubmissionsTask(BaseTask):
    priority = 10
    function = submit_pending_jobs



@logger_wraps()
async def trigger_garbage_collections(interval_between_calls: int = 60) -> None:
    """Trigger maintenance tasks on the Jobbergate API."""
    for path in (
        "/jobbergate/job-script-templates/upload/garbage-collector",
        "/jobbergate/job-scripts/upload/garbage-collector",
        "/jobbergate/job-scripts/clean-unused-entries",
    ):
        await asyncio.sleep(interval_between_calls)
        logger.debug(f"Triggering {path=}")
        with handle_errors(f"Failed to trigger {path=}", do_except=log_error):
            response = await backend_client.delete(path)
            response.raise_for_status()


class GarbageCollectionTask(BaseTask):
    enabled = SETTINGS.TASK_GARBAGE_COLLECTION_HOUR is not None
    function = trigger_garbage_collections
    scheduler_kwargs = dict(
        trigger="cron",
        hour=SETTINGS.TASK_GARBAGE_COLLECTION_HOUR,
        misfire_grace_time=None,
        kwargs=dict(interval_between_calls=SETTINGS.TASK_JOBS_INTERVAL_SECONDS),
    )
