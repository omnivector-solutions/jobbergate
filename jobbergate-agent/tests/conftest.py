import contextlib
from datetime import datetime, timezone
from typing import Callable
from unittest import mock

import httpx
import pytest
import respx
from jose.jwt import encode
from loguru import logger

from jobbergate_agent.settings import SETTINGS


@pytest.fixture(autouse=True)
def mock_cluster_api_cache_dir(tmp_path):
    _cache_dir = tmp_path / ".cache/jobbergate-agent/cluster-api"
    with mock.patch("jobbergate_agent.clients.cluster_api.CACHE_DIR", new=_cache_dir):
        yield _cache_dir


@pytest.fixture
def caplog(caplog):
    """
    Make the ``caplog`` fixture work with the loguru logger.
    """
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def tweak_settings() -> Callable[..., contextlib._GeneratorContextManager]:
    """
    Provides a fixture to use as a context manager where the project settings may be
    temporarily changed.
    """

    @contextlib.contextmanager
    def _helper(**kwargs):
        """
        Context manager for tweaking app settings temporarily.
        """
        previous_values = {}
        for key, value in kwargs.items():
            previous_values[key] = getattr(SETTINGS, key)
            setattr(SETTINGS, key, value)
        try:
            yield
        finally:
            for key, value in previous_values.items():
                setattr(SETTINGS, key, value)

    return _helper


@pytest.fixture()
def token_content() -> str:
    one_minute_from_now = int(datetime.now(tz=timezone.utc).timestamp()) + 60
    return encode(dict(exp=one_minute_from_now), key="dummy-key", algorithm="HS256")


@pytest.fixture()
async def mock_access_token(token_content):
    """
    Fixture to mock the access token.
    """
    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(access_token=token_content),
            )
        )
        yield
