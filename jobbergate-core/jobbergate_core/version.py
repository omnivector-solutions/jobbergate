"""
Provide the version of the package.
"""

from importlib import metadata


def get_version():
    """
    Get the version of the package.
    """
    try:
        return metadata.version(__package__ or __name__)
    except metadata.PackageNotFoundError:
        return "unknown"


__version__ = get_version()
