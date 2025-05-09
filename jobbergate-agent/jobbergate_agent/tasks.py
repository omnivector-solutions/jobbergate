"""Task definitions for the Jobbergate Agent."""

from jobbergate_agent.internals.update import self_update_agent
from jobbergate_agent.jobbergate.report_health import report_health_status
from jobbergate_agent.jobbergate.submit import submit_pending_jobs
from jobbergate_agent.jobbergate.update import update_active_jobs
from jobbergate_agent.settings import SETTINGS
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
