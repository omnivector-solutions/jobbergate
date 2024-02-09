"""
Provide the task scheduler for the agent and the main loop to run it.

Custom tasks can be added to the agent as installable plugins, which are discovered at runtime.

References:
    https://github.com/agronholm/apscheduler
    https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins
"""
from typing import Protocol, Union

from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import BaseScheduler
from buzz import handle_errors

from jobbergate_agent.utils.logging import logger, logger_wraps
from jobbergate_agent.utils.plugin import load_plugins


@logger_wraps()
def schedule_tasks(scheduler: BaseScheduler) -> None:
    """Discovery and schedule all tasks to be run by the agent."""

    for name, task_class in sorted(load_plugins("tasks").items(), key=lambda i: i[1].priority):
        with handle_errors(
            f"Failed to execute and thus to schedule the task {name=}",
            raise_exc_class=RuntimeError,
            do_except=lambda params: logger.error(params.final_message),
        ):
            task = task_class()
            if task.enabled:
                job = scheduler.add_job(
                    task.function,
                    **task.scheduler_kwargs,
                )
                job.name = name


@logger_wraps()
def init_scheduler() -> BaseScheduler:
    """Initialize the scheduler and schedule all tasks."""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    schedule_tasks(scheduler)
    return scheduler


@logger_wraps()
def shut_down_scheduler(scheduler: BaseScheduler, wait: bool = True) -> None:
    """Shutdown the scheduler."""
    scheduler.shutdown(wait)
