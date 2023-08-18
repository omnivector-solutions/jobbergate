import contextlib
import random
import string
from datetime import datetime, timezone
from unittest import mock

import httpx
import pytest
import respx
from jose.jwt import encode
from loguru import logger

from jobbergate_agent.settings import SETTINGS


@pytest.fixture
def random_word():
    """
    Fixture to provide a helper method to return a
    random string containing a fixed number of chars
    """

    def _helper(length: int = 30):
        """
        Args:
            length (int): String's  final length
        """
        letters = string.ascii_lowercase
        return "".join(random.choice(letters) for i in range(length))

    return _helper


@pytest.fixture(autouse=True)
def mock_cluster_api_cache_dir(tmp_path):
    _cache_dir = tmp_path / ".cache/jobbergate-agent/cluster-api"
    with mock.patch("jobbergate_agent.identity.cluster_api.CACHE_DIR", new=_cache_dir):
        yield _cache_dir


@pytest.fixture(autouse=True)
def mock_slurmrestd_api_cache_dir(tmp_path):
    _cache_dir = tmp_path / ".cache/jobbergate-agent/slurmrestd"
    with mock.patch("jobbergate_agent.identity.slurmrestd.CACHE_DIR", new=_cache_dir):
        yield _cache_dir


@pytest.fixture(autouse=True)
def slurmrestd_jwt_key_string():
    yield "DUMMY-JWT-SECRET"


@pytest.fixture(autouse=True)
def slurmrestd_jwt_key_path(tmp_path, slurmrestd_jwt_key_string):
    _jwt_dir = tmp_path / "jwt.key"
    _jwt_dir.write_text(slurmrestd_jwt_key_string)
    with mock.patch.object(SETTINGS, "SLURMRESTD_JWT_KEY_PATH", new=_jwt_dir.as_posix()):
        yield _jwt_dir


@pytest.fixture(autouse=True)
def mock_slurmrestd_acquire_token(mocker):
    mocker.patch(
        "jobbergate_agent.identity.slurmrestd.acquire_token",
        return_value="default-dummy-token",
    )


@pytest.fixture
def caplog(caplog):
    """
    Make the ``caplog`` fixture work with the loguru logger.
    """
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


@pytest.fixture
def tweak_settings():
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
