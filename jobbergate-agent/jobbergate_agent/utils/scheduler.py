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


scheduler = AsyncIOScheduler()


class JobbergateTask(Protocol):
    """Protocol to be implemented by any task that is expected to run on the scheduler."""

    def __call__(self, scheduler: BaseScheduler) -> Union[Job, None]:
        """
        Specify a callable used to schedule a task and return the resulting job.

        This is handled to client code to give them the opportunity to handle
        their own configuration and to access the rich flexibility of the scheduler API.

        None can also be returned if no task is going to be scheduled due to internal business logic.
        """
        ...


@logger_wraps()
def schedule_tasks(scheduler: BaseScheduler) -> None:
    """Discovery and schedule all tasks to be run by the agent."""

    for name, task_function in load_plugins("tasks").items():
        with handle_errors(
            f"Failed to execute and thus to schedule the task {name=}",
            raise_exc_class=RuntimeError,
            do_except=lambda params: logger.error(params.final_message),
        ):
            job = task_function(scheduler=scheduler)

        if job is not None:
            job.name = name


@logger_wraps()
def init_scheduler() -> BaseScheduler:
    """Initialize the scheduler and schedule all tasks."""
    scheduler.start()
    schedule_tasks(scheduler)
    return scheduler


@logger_wraps()
def shut_down_scheduler(scheduler: BaseScheduler, wait: bool = True) -> None:
    """Shutdown the scheduler."""
    scheduler.shutdown(wait)
