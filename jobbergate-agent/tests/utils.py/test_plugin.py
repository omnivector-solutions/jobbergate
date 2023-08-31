"""Test the plugin module."""
from unittest import mock

import pytest

from jobbergate_agent.tasks import active_submissions_task, garbage_collection_task, pending_submissions_task
from jobbergate_agent.utils.plugin import load_plugins
from jobbergate_agent.utils.user_mapper import SingleUserMapper


def test_discover_tasks__success():
    """Test that discover_tasks returns the expected result."""
    expected_result = {
        "active-jobs": active_submissions_task,
        "pending-jobs": pending_submissions_task,
        "garbage-collection": garbage_collection_task,
    }
    actual_result = load_plugins("tasks")

    assert actual_result == expected_result


def test_discover_user_mappers__success():
    """Test that discover_user_mappers returns the expected result."""
    expected_result = {"single-user-mapper": SingleUserMapper}
    actual_result = load_plugins("user_mapper")

    assert actual_result == expected_result


@mock.patch("jobbergate_agent.utils.plugin.entry_points")
def test_discover__fail_to_load(mocked_entry_points):
    """Test that discover_tasks raises RuntimeError when fails to load."""
    mocked_pluging = mock.Mock()
    mocked_pluging.load.side_effect = Exception("Test")
    mocked_entry_points.return_value = [mocked_pluging]

    with pytest.raises(RuntimeError, match="^Failed to load plugin"):
        load_plugins("non-existent-plugin")
