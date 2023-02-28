import pendulum
import pytest
from jose.jwt import encode


@pytest.fixture(scope="session")
def time_now():
    """
    Return a pendulum instance with a fixed time.
    """
    time_now = pendulum.datetime(2020, 1, 1, tz="UTC")
    pendulum.set_test_now(time_now)

    yield time_now

    pendulum.set_test_now(None)


@pytest.fixture(scope="session")
def jwt_token(time_now):
    """
    This fixture will create a JWT token using the jose package.
    """

    def helper(expiration_time=time_now, **kwargs):

        payload = {
            "exp": expiration_time.int_timestamp,
            **kwargs,
        }
        jwt_token = encode(payload, "fake-secret", algorithm="HS256")

        return jwt_token

    return helper
