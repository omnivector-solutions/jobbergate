"""Test the plugin module."""

from jobbergate_agent.tasks import (
    active_submissions_task,
    pending_submissions_task,
    self_update_task,
    status_report_task,
)
from jobbergate_agent.utils.plugin import load_plugins
from jobbergate_agent.utils.user_mapper import SingleUserMapper


def test_discover_tasks__success():
    """Test that discover_tasks returns the expected result."""
    expected_result = {
        "active-jobs": active_submissions_task,
        "pending-jobs": pending_submissions_task,
        "report-status": status_report_task,
        "self-update": self_update_task,
    }
    actual_result = load_plugins("tasks")

    assert actual_result == expected_result


def test_discover_user_mappers__success():
    """Test that discover_user_mappers returns the expected result."""
    expected_result = {"single-user-mapper": SingleUserMapper}
    actual_result = load_plugins("user_mapper")

    assert actual_result == expected_result
