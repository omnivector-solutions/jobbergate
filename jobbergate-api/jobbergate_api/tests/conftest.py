"""
Configuration of pytest.
"""

import contextlib
import dataclasses
import datetime
import random
import string
import tarfile
import typing
from io import BytesIO

import pytest
import sqlalchemy
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.config import settings
from jobbergate_api.main import app
from jobbergate_api.metadata import metadata
from jobbergate_api.storage import build_db_url, database

# Charset for producing random strings
CHARSET = string.ascii_letters + string.digits + string.punctuation


@pytest.fixture(autouse=True, scope="session")
async def enforce_empty_database():
    """
    Make sure our database is empty at the end of each test.
    """
    engine = sqlalchemy.create_engine(build_db_url())
    metadata.create_all(engine)
    yield

    await database.connect()
    for table in (applications_table, job_scripts_table, job_submissions_table):
        count = await database.execute(sqlalchemy.select([sqlalchemy.func.count()]).select_from(table))
        assert count == 0
    await database.disconnect()

    metadata.drop_all(engine)


@pytest.fixture(autouse=True)
@pytest.mark.enforce_empty_database()
async def startup_event_force():
    """
    Force the async event loop to begin.
    """
    async with LifespanManager(app):
        yield


@pytest.fixture(autouse=True)
def enforce_mocked_oidc_provider(mock_openid_server):
    """
    Enforce that the OIDC provider used by armasec is the mock_openid_server provided as a fixture.

    No actual calls to an OIDC provider will be made.
    """
    yield


@pytest.fixture
async def client():
    """
    Provide a client that can issue fake requests against fastapi endpoint functions in the backend.
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def inject_security_header(client, build_rs256_token):
    """
    Provide a helper method that will inject a security token into the requests for a test client.

    If no permissions are provided, the security token will still be valid but will not carry any permissions.
    Uses the `build_rs256_token()` fixture from the armasec package. If `client_id` is provided, it
    will be injected into the custom identity claims.
    """

    def _helper(
        owner_email: str,
        *permissions: typing.List[str],
        client_id: typing.Optional[str] = None,
    ):
        claim_overrides = dict(
            email=owner_email,
            client_id=client_id,
            permissions=permissions,
        )
        token = build_rs256_token(claim_overrides=claim_overrides)
        client.headers.update({"Authorization": f"Bearer {token}"})

    return _helper


@pytest.fixture
def time_frame():
    """
    Provide a fixture to use as a context manager for asserting events happened in a window of time.
    """

    @dataclasses.dataclass
    class TimeFrame:
        """
        Class for storing the beginning and end of a time frame.
        """

        now: datetime.datetime
        later: typing.Optional[datetime.datetime]

        def __contains__(self, moment: datetime.datetime):
            """
            Check if a given moment falls within a time-frame.
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
        window.later = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)

    return _helper


@pytest.fixture
def tweak_settings():
    """
    Provide a fixture to use as a context manager where the app settings may be temporarily changed.
    """

    @contextlib.contextmanager
    def _helper(**kwargs):
        """
        Context manager for tweaking app settings temporarily.
        """
        previous_values = {}
        for (key, value) in kwargs.items():
            previous_values[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
        for (key, value) in previous_values.items():
            setattr(settings, key, value)

    return _helper


@pytest.fixture
def make_dummy_file(tmp_path):
    """
    Provide a fixture that will generate a temporary file with ``size`` random bytes of text data.
    """

    def _helper(filename, size=100):
        """
        Auxillery function that builds the temporary file.
        """
        text = "".join(random.choice(CHARSET) for i in range(size))
        dummy_path = tmp_path / filename
        dummy_path.write_text(text)
        return dummy_path

    return _helper


@pytest.fixture
def make_files_param():
    """
    Provide a fixture to use as a context manager that builds the ``files`` parameter.

    Open the supplied file and build a ``files`` param appropriate for using multi-part file uploads with the
    client.
    """

    @contextlib.contextmanager
    def _helper(file_path):
        """
        Context manager that opens the file and yields the ``files`` param from it.
        """
        with open(file_path, "r") as file_handle:
            yield dict(upload_file=(file_path.name, file_handle, "text/plain"))

    return _helper


@pytest.fixture
def s3_object():
    """
    Provide a fixture that creates a test s3 object.
    """
    return {"Body": open("jobbergate_api/tests/apps/job_scripts/test_files/jobbergate.tar.gz", "rb")}


@pytest.fixture
def s3_object_as_tar(s3_object):
    """
    Provide a fixture that returns a tarball created from an s3 object.
    """
    return tarfile.open(fileobj=BytesIO(s3_object["Body"].read()))
