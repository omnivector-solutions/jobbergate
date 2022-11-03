"""
Provide the version of the package.
"""

from importlib import metadata

import toml


def get_version_from_metadata() -> str:
    """
    Get the version from the metadata.

    This is the preferred method of getting the version, but only works if the
    package is properly installed in a Python environment.
    """
    return metadata.version(__package__ or __name__)


def get_version_from_poetry() -> str:
    """
    Get the version from pyproject.toml.

    This is a fallback method if the package is not installed, but just copied
    and accessed locally, like in a Docker image.
    """
    return toml.load("pyproject.toml")["tool"]["poetry"]["version"]


def get_version() -> str:
    """
    Get the version from the metadata if available, otherwise from pyproject.toml.

    Returns "unknown" if both methods fail.
    """
    try:
        return get_version_from_metadata()
    except metadata.PackageNotFoundError:
        try:
            return get_version_from_poetry()
        except (FileNotFoundError, KeyError):
            return "unknown"


__version__ = get_version()
