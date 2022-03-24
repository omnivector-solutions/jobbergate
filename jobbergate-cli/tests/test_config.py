import pydantic
import pytest

from jobbergate_cli.config import Settings


def test_SENTRY_TRACE_RATE__requires_float_in_valid_range():
    assert Settings(SENTRY_TRACE_RATE=0.5)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=0.0)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=1.1)
