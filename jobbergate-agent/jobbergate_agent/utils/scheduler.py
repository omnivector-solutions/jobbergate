"""
Provide the task scheduler for the agent and the main loop to run it.

Custom tasks can be added to the agent as installable plugins, which are discovered at runtime.

References:
    https://github.com/agronholm/apscheduler
    https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins
"""

from typing import Optional, Protocol

from apscheduler import AsyncScheduler
from buzz import handle_errors

from jobbergate_agent.utils.logging import logger, logger_wraps
from jobbergate_agent.utils.plugin import load_plugins


scheduler = AsyncScheduler()

# Track schedule IDs so they can be cleared during self-update
_schedule_ids: list[str] = []


class JobbergateTask(Protocol):
    """Protocol to be implemented by any task that is expected to run on the scheduler."""

    async def __call__(self, scheduler: AsyncScheduler) -> Optional[str]:
        """
        Specify an async callable used to schedule a task and return the resulting schedule ID.

        None can also be returned if no task is going to be scheduled due to internal business logic.
        """
        ...


@logger_wraps()
async def schedule_tasks(scheduler: AsyncScheduler) -> None:
    """Discover and schedule all tasks to be run by the agent."""
    global _schedule_ids

    for name, task_function in load_plugins("tasks").items():
        with handle_errors(
            f"Failed to execute and thus to schedule the task {name=}",
            raise_exc_class=RuntimeError,
            do_except=lambda params: logger.error(params.final_message),
        ):
            schedule_id = await task_function(scheduler=scheduler)

        if schedule_id is not None:
            _schedule_ids.append(schedule_id)
            logger.debug(f"Scheduled task {name!r} with schedule ID {schedule_id}")


@logger_wraps()
async def clear_schedules(scheduler: AsyncScheduler) -> None:
    """Remove all tracked schedules (used during self-update)."""
    global _schedule_ids

    for sid in list(_schedule_ids):
        try:
            await scheduler.remove_schedule(sid)
        except Exception as exc:
            logger.warning(f"Could not remove schedule {sid}: {exc}")
    _schedule_ids.clear()
