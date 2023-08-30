"""
Provide the version of the package.
"""
from importlib import metadata


try:
    __version__ = metadata.version(__package__ or __name__)
except metadata.PackageNotFoundError:
    __version__ = "unknown"
