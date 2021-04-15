"""
Configuration of pytest
"""
import os

from fastapi.testclient import TestClient
from jose import jwt
from pytest import fixture

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

    count = await database.fetch_all("SELECT COUNT(*) FROM users")
    assert count[0][0] == 0


@fixture
async def client():
    """
    A client that can issue fake requests against fastapi endpoint functions in the backend
    """
    # defer import of main to prevent accidentally importing storage too early
    from jobbergateapi2.main import app as backend_app

    encoded_jwt = jwt.encode({"sub": "user1@email.com"}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    with TestClient(backend_app) as client:
        token = f"bearer {encoded_jwt}"
        client.headers.update({"Authorization": token})
        yield client
