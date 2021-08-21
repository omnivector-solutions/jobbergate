"""
Configuration of pytest
"""
import datetime
import os
import typing

from asgi_lifespan import LifespanManager
from fastapi.testclient import TestClient
from httpx import AsyncClient
from jose import jwt
from pytest import fixture
from armasec.managers import TestTokenManager

from jobbergateapi2.main import app
from jobbergateapi2.config import settings

TESTING_DB_FILE = "./sqlite-testing.db"
settings.DATABASE_URL = f"sqlite:///{TESTING_DB_FILE}"

settings.TEST_ENV = True


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
    os.remove(TESTING_DB_FILE)


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


@fixture
def manager():
    """
    Returns a TestTokenManager behaves the same as the app's TokenManager but with test helpers added
    """
    return TestTokenManager(
        secret=settings.ARMASEC_SECRET,
        algorithm=settings.ARMASEC_ALGORITHM,
        issuer=settings.ARMASEC_ISSUER,
        audience=settings.ARMASEC_AUDIENCE,
    )


@fixture(autouse=True)
async def startup_event_force():
    async with LifespanManager(app):
        yield



@fixture
async def client(startup_event_force):
    """
    A client that can issue fake requests against fastapi endpoint functions in the backend
    """
    with AsyncClient(backend_app, base_url="http://test") as client:
        yield client


@fixture
async def inject_security_header(client, manager):
    def _helper(
        owner_id: str,
        permissions: typing.List[str],
        expires_in_minutes: int = 0,
    ):
        token_payload = TokenPayload(
            sub=owner_id,
            permissions=permissions,
            expire=datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_in_minutes),
        )
        client.headers.update(manager.pack_header(token_payload))
    return _helper
