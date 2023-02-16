"""
Provide the version of the package.
"""
try:
    from importlib import metadata  # type: ignore
except ImportError:
    import importlib_metadata as metadata  # type: ignore # Python < 3.8

__version__ = metadata.version(__package__ or __name__)
