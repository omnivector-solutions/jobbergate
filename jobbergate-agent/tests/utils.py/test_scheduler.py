from unittest import mock

import pytest

from jobbergate_agent.utils.scheduler import (
    AsyncIOScheduler,
    init_scheduler,
    load_plugins,
    schedule_tasks,
    shut_down_scheduler,
)


@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
def test_schedule_tasks__success(mocked_plugins):
    """Test that schedule_tasks returns the expected result."""

    discovered_functions = load_plugins("tasks")
    mocked_functions = {name: mock.Mock() for name in discovered_functions.keys()}

    mocked_plugins.return_value = mocked_functions

    scheduler = AsyncIOScheduler()
    schedule_tasks(scheduler)

    mocked_plugins.assert_called_once_with("tasks")
    assert all(m.call_count == 1 for m in mocked_functions.values())
    assert all(m.call_args(scheduler=scheduler) for m in mocked_functions.values())


@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
def test_schedule_tasks__fails(mocked_plugins):
    """Test that schedule_tasks raises RuntimeError when fails to schedule a task."""

    mocked_functions = {"supposed-to-fail": mock.Mock(side_effect=Exception("Test"))}

    mocked_plugins.return_value = mocked_functions

    scheduler = AsyncIOScheduler()

    with pytest.raises(RuntimeError, match="^Failed to execute"):
        schedule_tasks(scheduler)

    mocked_plugins.assert_called_once_with("tasks")


def test_scheduler_end_to_end(tweak_settings):
    """Test that scheduler can start, get the tasks and shutdown properly."""
    with tweak_settings(TASK_SELF_UPDATE_INTERVAL_SECONDS=60):
        scheduler = init_scheduler()

    assert scheduler.running is True
    assert {job.name for job in scheduler.get_jobs()} == {
        "active-jobs",
        "pending-jobs",
        "report-status",
        "self-update",
    }

    shut_down_scheduler(scheduler, wait=False)

    # TODO: Find a way to wait for the scheduler to shut down.
    # assert scheduler.running is False
