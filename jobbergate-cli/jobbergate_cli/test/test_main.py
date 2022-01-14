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
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiaHR0cHM6Ly93d3cuYXJtYWRhLWhwYy5jb20iOnsidXNlcl9lbWFpbCI6Im93bmVyMUBvcmcuY29tIn0sImV4cCI6MTYzNzMzNjU3M30.cQZg-iG95FChU1tassJDnlc9Q72xMKJ33EFAKCQde7TiPrw-tBMiDKar0wMdLknXSQZdcL54QAj47rEHg9fkqo1rrVnAqBhLKD-yBLhpHYaHl7yb2Km_3u6f-MkfXsVcWKzS0xveQYb5SdkkqCXaRbJca2BSQhiJh9ulQb3bhESo6JebLYsO8l86c6IEkLz5yek862rs2HdZKPnrqs1nOvkzXMnMyUqxGedY5BM4GpUURh11ob4Z9DgOm5Yx2v9RwpFGyN7MkTExrivLib7m5gGd4PQiHiQKZUy3-tI-S1FW29RZU2HC7zHCnvlLcKzQslyeTIUWVjDOl-nXmUsjUw"  # noqa


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
    Do I successfully parse tokens from the cache? Do I identify invalid tokens?
    """
    freezer.move_to(when)
    ctx_obj = {}
    if is_valid:
        assert main.init_access_token(ctx_obj)
        assert "identity" in ctx_obj
    else:
        with pytest.raises(click.ClickException, match="The auth token is expired"):
            main.init_access_token(ctx_obj)
