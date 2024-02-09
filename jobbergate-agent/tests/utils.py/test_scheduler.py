from unittest import mock

import pytest

from jobbergate_agent.utils.scheduler import (
    AsyncIOScheduler,
    init_scheduler,
    load_plugins,
    schedule_tasks,
    shut_down_scheduler,
)
from jobbergate_agent.tasks import BaseTask
from jobbergate_agent.settings import SETTINGS


mock_foo = mock.Mock()

class FooTask(BaseTask):
    function = mock_foo
    priority = 1


mock_bar = mock.Mock()

class BarTask(BaseTask):
    function = mock_bar
    priority = 0


mock_baz = mock.Mock()

class BazTask(BaseTask):
    function = mock_baz
    enabled = False


@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
def test_schedule_tasks__success(mocked_plugins):
    """Test that schedule_tasks adds enabled tasks to the schedule by priority."""

    mocked_plugins.return_value = dict(
        foo=FooTask,
        bar=BarTask,
        baz=BazTask,
    )
    mock_scheduler = mock.Mock()
    schedule_tasks(mock_scheduler)

    mocked_plugins.assert_called_once_with("tasks")
    assert mock_scheduler.add_job.call_count == 2
    mock_scheduler.add_job.assert_has_calls(
        [
            mock.call(
                mock_bar,
                trigger="interval",
                seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS,
            ),
            mock.call(
                mock_foo,
                trigger="interval",
                seconds=SETTINGS.TASK_JOBS_INTERVAL_SECONDS,
            ),
        ]
    )


@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
def test_schedule_tasks__fails(mocked_plugins):
    """Test that schedule_tasks raises RuntimeError when fails to schedule a task."""

    mocked_plugins.return_value = dict(
        foo=FooTask,
        bar=BarTask,
        baz=BazTask,
    )
    mock_scheduler = mock.Mock()
    mock_scheduler.add_job.side_effect = RuntimeError
    with pytest.raises(RuntimeError, match="Failed to execute and thus to schedule the task name='bar'"):
        schedule_tasks(mock_scheduler)


def test_scheduler_end_to_end(tweak_settings):
    """Test that scheduler can start, get the tasks and shutdown properly."""
    scheduler = init_scheduler()

    assert scheduler.running is True
    assert {job.name for job in scheduler.get_jobs()} == {
        "active-jobs",
        "garbage-collection",
        "pending-jobs",
    }

    shut_down_scheduler(scheduler, wait=False)

    # TODO: Find a way to wait for the scheduler to shut down.
    # assert scheduler.running is False
