"""
Unit test helper functions in main
"""
import pathlib
from unittest.mock import create_autospec, patch

import click
import pytest
from pytest import fixture, mark

from jobbergate_cli import config, main


@fixture
def token_cache_mock(sample_token):
    """
    Mock access to the filesystem path where the jwt token is cached
    """
    mock_access_token_path = create_autospec(pathlib.Path, instance=True)
    mock_access_token_path.exists.return_value = True
    mock_access_token_path.read_text.return_value = sample_token

    mock_refresh_token_path = create_autospec(pathlib.Path, instance=True)
    mock_refresh_token_path.exists.return_value = False

    with patch.object(config.settings, "JOBBERGATE_API_ACCESS_TOKEN_PATH", mock_access_token_path):
        with patch.object(config.settings, "JOBBERGATE_API_REFRESH_TOKEN_PATH", mock_refresh_token_path):
            yield (mock_access_token_path, mock_refresh_token_path)


@fixture
def sample_token():
    """
    A sample JWT that contains info needed for auth through the jobbergate-cli.
    The token expires 2021-11-19 15:52:53.
    """
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiaHR0cHM6Ly90ZXN0LWRvbWFpbi50ZXN0Ijp7InVzZXJfZW1haWwiOiJvd25lcjFAb3JnLmNvbSJ9LCJleHAiOjE2MzczMzY1NzN9.wfXxrwvVSQrirQn7D_tDCNAPPk-jmGMxaJMiuWC7iaU"  # noqa


@mark.parametrize(
    "when,is_valid",
    [
        ["2021-11-19 00:00:00", True],
        ["2021-11-19 23:59:59", False],
    ],
    ids=[
        "dwf;valid",
        "dwf;expired",
    ],
)
@mark.freeze_time()
@mark.usefixtures("token_cache_mock")
def test_init_access_token(when, is_valid, freezer):
    """
    Do I successfully parse an access token from the cache? Do I identify an invalid access token?
    """
    freezer.move_to(when)
    ctx_obj = {}
    if is_valid:
        assert main.init_access_token(ctx_obj)
        assert "identity" in ctx_obj
    else:
        with pytest.raises(click.ClickException, match="The auth token is expired"):
            main.init_access_token(ctx_obj)
