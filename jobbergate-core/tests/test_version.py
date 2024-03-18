"""
Test the module version.
"""

import toml

from jobbergate_core import __version__


def test_version_matches_poetry():
    """
    Test that the version matches the version in pyproject.toml.

    It is necessary to replace alpha and beta by a and b when running
    prereleases on poetry 1.1.*, this can be removed for poetry 1.2.*,
    since the version scheme is already normalized.
    """
    poetry_version = toml.load("pyproject.toml")["tool"]["poetry"]["version"]
    poetry_version = poetry_version.replace("-alpha.", "a").replace("-beta.", "b")

    assert __version__ == poetry_version
