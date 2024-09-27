from unittest import mock

import httpx
import pytest
import respx

from jobbergate_agent.internals.update import (
    _fetch_upstream_version_info,
    _need_update,
    _update_package,
    self_update_agent,
)
from jobbergate_agent.settings import SETTINGS


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize("upstream_version", ["1.0.0", "1.0.1", "1.1.0", "2.0.0"])
async def test__fetch_upstream_version_info__success(upstream_version: str):
    """Test that _fetch_upstream_version_info returns the expected result."""
    async with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/openapi.json").mock(
            return_value=httpx.Response(200, json={"info": {"version": upstream_version}})
        )

        assert await _fetch_upstream_version_info() == upstream_version


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize("http_code", [404, 500])
async def test__fetch_upstream_version_info__check_http_error(http_code: int):
    """Test that _fetch_upstream_version_info raises error on HTTP error."""
    async with respx.mock:
        with pytest.raises(httpx.HTTPStatusError):
            respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/openapi.json").mock(return_value=httpx.Response(http_code))

            await _fetch_upstream_version_info()


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "current_version, upstream_version, expected_result",
    [
        ("1.0.0", "1.0.0", False),  # Same version
        ("1.0.0", "2.0.0", False),  # Different major version
        ("1.0.0", "1.1.0", True),  # Minor version update available
        ("1.0.0", "1.0.1", True),  # Patch version update available
        ("2.0.0", "1.0.0", False),  # Major version rollback
        ("1.2.0", "1.1.0", True),  # Minor version rollback
        ("1.0.1", "1.0.0", True),  # Patch version rollback
    ],
)
def test_need_update(current_version: str, upstream_version: str, expected_result: bool):
    """Test that _need_update returns the expected result."""
    assert _need_update(current_version, upstream_version) is expected_result


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "current_version, upstream_version",
    [
        ("1.0", "1.0.1"),  # Improperly formatted current version
        ("1.0.0", "1.0"),  # Improperly formatted upstream version
        ("1", "2"),  # Major version with no minor/patch
        ("1.0.1a", "1.1.0"),  # Pre-release improperly formatted
        ("1.0.1", "1.0.10b"),  # Pre-release improperly formatted
        ("1.0.9a1", "1.0.9a2"),  # Alpha version is not an allowed format
    ],
)
def test_need_update__check_improperly_formatted_versions(
    current_version: str,
    upstream_version: str,
):
    """Test that _need_update raises error on improperly formatted versions."""
    with pytest.raises(ValueError):
        _need_update(current_version, upstream_version)


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.parametrize(
    "version, executable",
    [
        ("1.0.0", "/dummy/foo"),
        ("1.0.1", "/dummy/bar"),
        ("1.1.0", "/dummy/baz"),
        ("2.0.0", "/dummy/qux"),
    ],
)
@mock.patch("jobbergate_agent.internals.update.subprocess")
@mock.patch("jobbergate_agent.internals.update.sys")
def test_update_package(mocked_sys: mock.MagicMock, mocked_subprocess: mock.MagicMock, version: str, executable: str):
    """Test that _update_package runs without error."""
    mocked_subprocess.check_call.return_value = None
    mocked_sys.executable = executable

    _update_package(version)

    mocked_subprocess.check_call.assert_called_once_with(
        [executable, "-m", "pip", "install", "--upgrade", f"jobbergate_agent=={version}"]
    )


@pytest.mark.usefixtures("mock_access_token")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "current_version, upstream_version, is_update_available",
    [
        ("1.0.0", "1.0.0", False),  # Same version
        ("1.0.0", "2.0.0", False),  # Different major version
        ("1.0.0", "1.1.0", True),  # Minor version update available
        ("1.0.0", "1.0.1", True),  # Patch version update available
        ("2.0.0", "1.0.0", False),  # Major version rollback
        ("1.2.0", "1.1.0", True),  # Minor version rollback
        ("1.0.1", "1.0.0", True),  # Patch version rollback
    ],
)
@mock.patch("jobbergate_agent.internals.update._fetch_upstream_version_info")
@mock.patch("jobbergate_agent.internals.update._update_package")
@mock.patch("jobbergate_agent.internals.update.version")
@mock.patch("jobbergate_agent.internals.update._need_update")
@mock.patch("jobbergate_agent.internals.update.scheduler")
@mock.patch("jobbergate_agent.internals.update.schedule_tasks")
async def test_self_update_agent(
    mocked_schedule_tasks: mock.MagicMock,
    mocked_scheduler: mock.MagicMock,
    mocked_need_update: mock.MagicMock,
    mocked_version: mock.MagicMock,
    mocked_update_package: mock.MagicMock,
    mocked_fetch_upstream_version_info: mock.MagicMock,
    current_version: str,
    upstream_version: str,
    is_update_available: bool,
):
    """Test that self_update_agent runs without error the expected logic.

    If an update is available, it is expected that the scheduler is shutdown
    and then restarted with the new version after the package update is done.
    """
    mocked_version.return_value = current_version
    mocked_fetch_upstream_version_info.return_value = upstream_version
    mocked_need_update.return_value = is_update_available
    mocked_scheduler.pause = mock.Mock()
    mocked_scheduler.resume = mock.Mock()

    await self_update_agent()

    mocked_version.assert_called_once_with("jobbergate_agent")
    mocked_fetch_upstream_version_info.assert_called_once_with()
    mocked_need_update.assert_called_once_with(current_version, upstream_version)
    if is_update_available:
        mocked_scheduler.pause.assert_called_once_with()
        mocked_update_package.assert_called_once_with(upstream_version)
        mocked_schedule_tasks.assert_called_once_with(mocked_scheduler)
        mocked_scheduler.resume.assert_called_once_with()

    else:
        mocked_scheduler.pause.assert_not_called()
        mocked_update_package.assert_not_called()
        mocked_schedule_tasks.assert_not_called()
        mocked_scheduler.resume.assert_not_called()
