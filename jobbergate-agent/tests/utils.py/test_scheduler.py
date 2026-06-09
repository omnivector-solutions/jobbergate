from unittest import mock
from unittest.mock import AsyncMock

import pytest

from jobbergate_agent.utils.scheduler import (
    AsyncScheduler,
    load_plugins,
    schedule_tasks,
)


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
async def test_schedule_tasks__success(mocked_plugins):
    """Test that schedule_tasks returns the expected result."""

    discovered_functions = load_plugins("tasks")
    mocked_functions = {name: AsyncMock(return_value="fake-schedule-id") for name in discovered_functions.keys()}

    mocked_plugins.return_value = mocked_functions

    async with AsyncScheduler() as scheduler:
        await schedule_tasks(scheduler)

    mocked_plugins.assert_called_once_with("tasks")
    assert all(m.call_count == 1 for m in mocked_functions.values())
    assert all(m.call_args(scheduler=scheduler) for m in mocked_functions.values())


@pytest.mark.asyncio
@mock.patch("jobbergate_agent.utils.scheduler.load_plugins")
async def test_schedule_tasks__fails(mocked_plugins):
    """Test that schedule_tasks raises RuntimeError when fails to schedule a task."""

    mocked_functions = {"supposed-to-fail": AsyncMock(side_effect=Exception("Test"))}

    mocked_plugins.return_value = mocked_functions

    async with AsyncScheduler() as scheduler:
        with pytest.raises(RuntimeError, match="^Failed to execute"):
            await schedule_tasks(scheduler)

    mocked_plugins.assert_called_once_with("tasks")
