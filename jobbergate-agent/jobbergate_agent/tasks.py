"""Task definitions for the Jobbergate Agent."""

from typing import Optional

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

from jobbergate_agent.internals.update import self_update_agent
from jobbergate_agent.jobbergate.report_health import report_health_status
from jobbergate_agent.jobbergate.submit import submit_pending_jobs
from jobbergate_agent.jobbergate.update import update_active_jobs
from jobbergate_agent.settings import SETTINGS


async def self_update_task(scheduler: AsyncScheduler) -> Optional[str]:
    """
    Schedule a task to self update the agent every ``TASK_SELF_UPDATE_INTERVAL_SECONDS`` seconds.
    """
    if SETTINGS.TASK_SELF_UPDATE_INTERVAL_SECONDS is None:
        return None
    return await scheduler.add_schedule(
        self_update_agent, IntervalTrigger(seconds=SETTINGS.TASK_SELF_UPDATE_INTERVAL_SECONDS)
    )


async def active_submissions_task(scheduler: AsyncScheduler) -> str:
    """
    Schedule a task to handle active jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return await scheduler.add_schedule(
        update_active_jobs, IntervalTrigger(seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)
    )


async def pending_submissions_task(scheduler: AsyncScheduler) -> str:
    """
    Schedule a task to submit pending jobs every ``TASK_JOBS_INTERVAL_SECONDS`` seconds.
    """
    return await scheduler.add_schedule(
        submit_pending_jobs, IntervalTrigger(seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS)
    )


async def status_report_task(scheduler: AsyncScheduler) -> str:
    """
    Schedule a task to report the status.
    """
    seconds_between_calls = SETTINGS.TASK_JOBS_INTERVAL_SECONDS
    return await scheduler.add_schedule(
        report_health_status,
        IntervalTrigger(seconds=seconds_between_calls),
        kwargs={"interval": seconds_between_calls},
    )
