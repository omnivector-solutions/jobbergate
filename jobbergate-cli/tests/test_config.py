import os
from pathlib import Path

import pydantic
import pytest

from jobbergate_cli.config import Settings, build_settings


def test_SENTRY_TRACE_RATE__requires_float_in_valid_range():
    assert Settings(SENTRY_TRACE_RATE=0.5)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=0.0)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=1.1)


def test_Validation_error__when_parameter_is_missing():
    original_value = os.environ.get("OIDC_DOMAIN")
    try:
        if "OIDC_DOMAIN" in os.environ:
            del os.environ["OIDC_DOMAIN"]

        with pytest.raises(SystemExit) as e:
            build_settings(_env_file=None)

        assert e.value.code == 1
    finally:
        if original_value is not None:
            os.environ["OIDC_DOMAIN"] = original_value


def test_cache_dir__expands_user_and_resolves():
    settings = Settings(JOBBERGATE_CACHE_DIR="~/.jobbergate-cli-prod")
    assert settings.JOBBERGATE_CACHE_DIR == Path.home() / ".jobbergate-cli-prod"
    assert settings.JOBBERGATE_CACHE_DIR.is_absolute()
