import contextlib
import pathlib

import pytest
from loguru import logger

from jobbergate_cli.config import settings


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture(autouse=True)
def clear_cache():
    """
    Remove any data left in the test cache.

    Data should not have been stored in the cache during tests, but sometimes mistakes are made.
    """

    def deltree(tree: pathlib.Path):
        for item in tree.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                deltree(item)

    deltree(settings.JOBBERGATE_CACHE_DIR)


@pytest.fixture
def tweak_settings():
    """
    Provides a fixture to use as a context manager where the cli settings may be temporarily changed.
    """

    @contextlib.contextmanager
    def _helper(**kwargs):
        """
        Context manager for tweaking app settings temporarily.
        """
        previous_values = {}
        for (key, value) in kwargs.items():
            previous_values[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
        for (key, value) in previous_values.items():
            setattr(settings, key, value)

    return _helper
