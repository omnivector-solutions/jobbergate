"""Test the plugin module."""

from jobbergate_agent.tasks import (
    active_submissions_task,
    pending_submissions_task,
    self_update_task,
    status_report_task,
)
from jobbergate_agent.user_mapper.ldap import user_mapper_factory
from jobbergate_agent.utils.plugin import load_plugins
from jobbergate_agent.user_mapper.single_user import SingleUserMapper


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
    expected_result = {"single-user-mapper": SingleUserMapper, "ldap-cached-mapper": user_mapper_factory}
    actual_result = load_plugins("user_mapper")

    assert actual_result == expected_result
