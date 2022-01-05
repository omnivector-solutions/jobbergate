"""
Configuration of pytest.
"""
import contextlib
import dataclasses
import datetime
import os
import typing

from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from pytest import fixture

from jobbergate_api.config import settings
from jobbergate_api.main import app


@fixture(scope="session", autouse=True)
def backend_testing_database():
    """
    Override whatever is set for DATABASE_URL during testing.
    """
    # defer import of storage until now, to prevent the database
    # from being initialized implicitly on import
    from jobbergate_api.storage import create_all_tables

    create_all_tables()
    yield
    os.remove("./sqlite-testing.db")


@fixture(autouse=True)
def enforce_testing_database():
    """
    Ensure that we are using a testing database.
    """
    from jobbergate_api.storage import database

    assert "-testing" in database.url.database


@fixture(autouse=True)
async def enforce_empty_database():
    """
    Make sure our database is empty at the end of each test.
    """
    yield
    from jobbergate_api.storage import database

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@fixture(autouse=True)
async def startup_event_force():
    async with LifespanManager(app):
        yield


@fixture(autouse=True)
def enforce_mocked_oidc_provider(mock_openid_server):
    """
    Enforce that the OIDC provider used by armada-security is the mock_openid_server provided as a fixture.
    No actual calls to an OIDC provider will be made.
    """
    yield


@fixture
async def client(startup_event_force):
    """
    A client that can issue fake requests against fastapi endpoint functions in the backend.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@fixture
async def inject_security_header(client, build_rs256_token):
    """
    Provides a helper method that will inject a security token into the requests for a test client. If no
    permisions are provided, the security token will still be valid but will not carry any permissions. Uses
    the `build_rs256_token()` fixture from the armasec package.
    """

    def _helper(owner_email: str, *permissions: typing.List[str]):
        token = build_rs256_token(
            claim_overrides={
                settings.ARMADA_CLAIMS_KEY: {"user_email": owner_email},
                "permissions": permissions,
            }
        )
        client.headers.update({"Authorization": f"Bearer {token}"})

    return _helper


@fixture
def time_frame():
    """
    Provides a fixture to use as a context manager where an event can be checked to have happened during the
    time-frame of the context manager.
    """

    @dataclasses.dataclass
    class TimeFrame:
        """
        Class for storing the beginning and end of a time frame."
        """

        now: datetime.datetime
        later: typing.Optional[datetime.datetime]

        def __contains__(self, moment: datetime.datetime):
            """
            Checks if a given moment falls within a time-frame.
            """
            if self.later is None:
                return False
            return moment >= self.now and moment <= self.later

    @contextlib.contextmanager
    def _helper():
        """
        Context manager for defining the time-frame for the time_frame fixture.
        """
        window = TimeFrame(now=datetime.datetime.utcnow().replace(microsecond=0), later=None)
        yield window
        window.later = datetime.datetime.utcnow()

    return _helper
