import contextlib
import pytest

from jobbergate_cli.config import settings


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
