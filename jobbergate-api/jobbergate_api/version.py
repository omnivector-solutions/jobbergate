"""
Provide the version of the package.
"""

import tomllib
from importlib import metadata


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
    with open("pyproject.toml", "rb") as file:
        return tomllib.load(file)["tool"]["poetry"]["version"]


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
