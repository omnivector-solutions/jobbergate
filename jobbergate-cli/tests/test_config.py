from pathlib import Path

import pydantic
import pytest

from jobbergate_cli.config import Settings


def test_SENTRY_TRACE_RATE__requires_float_in_valid_range():
    assert Settings(SENTRY_TRACE_RATE=0.5)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=0.0)

    with pytest.raises(pydantic.ValidationError):
        Settings(SENTRY_TRACE_RATE=1.1)


def test_cache_dir__expands_user_and_resolves():
    settings = Settings(JOBBERGATE_CACHE_DIR="~/.jobbergate-cli-prod")
    assert settings.JOBBERGATE_CACHE_DIR == Path.home() / ".jobbergate-cli-prod"
    assert settings.JOBBERGATE_CACHE_DIR.is_absolute()


@pytest.mark.parametrize("sbatch_path, is_onsite_mode", [[None, False], ["/usr/bin/sbatch", True]])
def test_is_onsite_mode__is_true_when_sbatch_path_is_set(sbatch_path, is_onsite_mode):
    settings = Settings(SBATCH_PATH=sbatch_path)
    assert settings.is_onsite_mode == is_onsite_mode
