"""
Test the module version.
"""

from importlib.metadata import PackageNotFoundError
from unittest import mock

from jobbergate_api.version import (
    __version__,
    get_version,
    get_version_from_metadata,
    get_version_from_poetry,
)


def test_get_version_from_metadata():
    """
    Test the function get_version_from_metadata.
    """
    assert get_version_from_metadata() == __version__


def test_get_version_from_poetry():
    """
    Test the function get_version_from_poetry.

    It is necessary to replace alpha and beta by a and b when running
    prereleases on poetry 1.1.*, this can be removed for poetry 1.2.*,
    since the version scheme is already normalized.
    """
    poetry_version = get_version_from_poetry().replace("-alpha.", "a").replace("-beta.", "b")
    assert poetry_version == __version__


@mock.patch("jobbergate_api.version.get_version_from_poetry")
@mock.patch("jobbergate_api.version.get_version_from_metadata")
class TestGetVersion:
    """
    Test class to group tests for the function get_version.
    """

    def test_get_version__success(
        self,
        mock_get_version_from_metadata,
        mock_get_version_from_poetry,
    ):
        """
        Test the function get_version.
        """
        desired_version = "1.2.3"
        mock_get_version_from_metadata.return_value = desired_version

        actual_version = get_version()
        assert actual_version == desired_version

        mock_get_version_from_metadata.assert_called_once()
        mock_get_version_from_poetry.assert_not_called()

    def test_get_version__package_not_found(
        self,
        mock_get_version_from_metadata,
        mock_get_version_from_poetry,
    ):
        """
        Test the function get_version when the package is not installed.
        """
        desired_version = "1.2.3"
        mock_get_version_from_poetry.return_value = desired_version
        mock_get_version_from_metadata.side_effect = PackageNotFoundError

        actual_version = get_version()
        assert actual_version == desired_version

        mock_get_version_from_metadata.assert_called_once()
        mock_get_version_from_poetry.assert_called_once()

    def test_get_version__package_and_toml_not_found(
        self,
        mock_get_version_from_metadata,
        mock_get_version_from_poetry,
    ):
        """
        Test the function get_version when the package and the file pyproject.toml are not found.
        """
        mock_get_version_from_metadata.side_effect = PackageNotFoundError
        mock_get_version_from_poetry.side_effect = FileNotFoundError

        assert get_version() == "unknown"

        mock_get_version_from_metadata.assert_called_once()
        mock_get_version_from_poetry.assert_called_once()
