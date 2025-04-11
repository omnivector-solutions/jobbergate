"""
Test the module version.
"""

from importlib import metadata
import toml

from jobbergate_core.version import get_version


def test_version__matches_poetry():
    """
    Test that the version matches the version in pyproject.toml.

    It is necessary to replace alpha and beta by a and b when running
    prereleases on poetry 1.1.*, this can be removed for poetry 1.2.*,
    since the version scheme is already normalized.
    """
    poetry_version = toml.load("pyproject.toml")["tool"]["poetry"]["version"]
    poetry_version = poetry_version.replace("-alpha.", "a").replace("-beta.", "b")

    assert get_version() == poetry_version


def test_version__fallback_to_unknown(mocker):
    """
    Test that the version is set to "unknown" if the package is not found.
    """
    with mocker.patch("importlib.metadata.version", side_effect=metadata.PackageNotFoundError):
        assert get_version() == "unknown"
