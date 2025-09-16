from typing import Generator

import pendulum
import pytest
from jose.jwt import encode

from jobbergate_core.auth.token import Token, TokenType


@pytest.fixture(scope="session")
def time_now() -> Generator[pendulum.DateTime, None, None]:
    """
    Return a pendulum instance with a fixed time.
    """
    time_now = pendulum.datetime(2020, 1, 1, tz="UTC")

    try:
        pendulum.travel_to(time_now, freeze=True)
        yield time_now
    finally:
        pendulum.travel_back()


@pytest.fixture(scope="session")
def jwt_token(time_now):
    """
    This fixture will create a JWT token using the jose package.
    """

    def helper(expiration_time=time_now, **kwargs) -> str:
        payload = {"exp": expiration_time.int_timestamp, **kwargs}
        jwt_token = encode(payload, "fake-secret", algorithm="HS256")
        return jwt_token

    return helper


@pytest.fixture
def valid_token(tmp_path, jwt_token):
    """
    Return a valid token.
    """
    return Token(
        content=jwt_token(expiration_time=pendulum.tomorrow()),
        cache_directory=tmp_path,
        label=TokenType.ACCESS.value,
    )


@pytest.fixture
def expired_token(tmp_path, jwt_token):
    """
    Return an expired token.
    """
    return Token(
        content=jwt_token(expiration_time=pendulum.yesterday()),
        cache_directory=tmp_path,
        label=TokenType.ACCESS.value,
    )
