"""Task definitions for the Jobbergate Agent."""

import asyncio
from typing import Union

from buzz import handle_errors
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.jobbergate.finish import finish_active_jobs
from jobbergate_agent.jobbergate.submit import submit_pending_jobs
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import log_error, logger_wraps
from jobbergate_agent.utils.scheduler import BaseScheduler, Job


def active_submissions_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to handle active jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return scheduler.add_job(finish_active_jobs, "interval", seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)


def pending_submissions_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to submit pending jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return scheduler.add_job(submit_pending_jobs, "interval", seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)


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


def garbage_collection_task(scheduler: BaseScheduler) -> Union[Job, None]:
    """
    Schedule a task to perform garbage collection every dat at.
    """
    if SETTINGS.TASK_GARBAGE_COLLECTION_HOUR is None:
        return None
    return scheduler.add_job(
        trigger_garbage_collections,
        "cron",
        hour=SETTINGS.TASK_GARBAGE_COLLECTION_HOUR,
        misfire_grace_time=None,
        kwargs=dict(interval_between_calls=SETTINGS.TASK_JOBS_INTERVAL_SECONDS),
    )
