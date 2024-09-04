"""Task definitions for the Jobbergate Agent."""

import asyncio
from typing import Union

from buzz import handle_errors
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.internals.update import self_update_agent
from jobbergate_agent.jobbergate.report_health import report_health_status
from jobbergate_agent.jobbergate.submit import submit_pending_jobs
from jobbergate_agent.jobbergate.update import update_active_jobs
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.logging import log_error, logger_wraps
from jobbergate_agent.utils.scheduler import BaseScheduler, Job


def self_update_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to self update the agent every ``TASK_SELF_UPDATE_INTERVAL_SECONDS`` seconds.
    """
    if SETTINGS.TASK_SELF_UPDATE_INTERVAL_SECONDS is None:
        return None
    return scheduler.add_job(self_update_agent, "interval", seconds=SETTINGS.TASK_SELF_UPDATE_INTERVAL_SECONDS)


def active_submissions_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to handle active jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return scheduler.add_job(update_active_jobs, "interval", seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)


def pending_submissions_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to submit pending jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return scheduler.add_job(submit_pending_jobs, "interval", seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)


def status_report_task(scheduler: BaseScheduler) -> Job:
    """
    Schedule a task to report the status.
    """
    seconds_between_calls = SETTINGS.TASK_JOBS_INTERVAL_SECONDS
    return scheduler.add_job(
        report_health_status, "interval", seconds=seconds_between_calls, kwargs={"interval": seconds_between_calls}
    )


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
    Schedule a task to perform garbage collection every dat at a specified time.
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
