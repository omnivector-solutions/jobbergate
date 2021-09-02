"""
Configuration of pytest
"""
import datetime
import os
import typing
import unittest

from armasec.token_payload import TokenPayload
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from pytest import fixture

from jobbergateapi2.config import settings
from jobbergateapi2.main import app
from jobbergateapi2.security import armasec_manager


@fixture(scope="session", autouse=True)
def backend_testing_database():
    """
    Override whatever is set for DATABASE_URL during testing
    """
    # defer import of storage until now, to prevent the database
    # from being initialized implicitly on import
    from jobbergateapi2.storage import create_all_tables

    create_all_tables()
    yield
    os.remove("./sqlite-testing.db")


@fixture(autouse=True)
def enforce_testing_database():
    """
    Are you sure we're in a testing database?
    """
    from jobbergateapi2.storage import database

    assert "-testing" in database.url.database


@fixture(autouse=True)
async def enforce_empty_database():
    """
    Make sure our database is empty at the end of each test
    """
    yield
    from jobbergateapi2.storage import database

    count = await database.fetch_all("SELECT COUNT(*) FROM applications")
    assert count[0][0] == 0


@fixture(autouse=True)
async def startup_event_force():
    async with LifespanManager(app):
        yield


@fixture
async def client(startup_event_force):
    """
    A client that can issue fake requests against fastapi endpoint functions in the backend
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@fixture
async def inject_security_header(client):
    """
    Provides a helper method that will inject a security token into the requests for a test client. If no
    permisions are provided, the security token will still be valid but will not carry any permissions
    """

    def _helper(
        owner_id: str, *permissions: typing.List[str], expires_in_minutes: int = 0,
    ):
        token_payload = TokenPayload(
            sub=owner_id,
            permissions=permissions,
            expire=datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes),
        )
        client.headers.update(armasec_manager.pack_header(token_payload))

    return _helper
