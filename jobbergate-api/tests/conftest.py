"""Configuration of pytest."""

import asyncio
import contextlib
import dataclasses
import datetime
import random
import string
import typing
from contextlib import asynccontextmanager
from textwrap import dedent
from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient, Response, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependencies import get_bucket_name, get_bucket_url, s3_bucket, service_factory
from jobbergate_api.apps.models import Base
from jobbergate_api.config import settings
from jobbergate_api.main import app
from jobbergate_api.storage import engine_factory

# Charset for producing random strings
CHARSET = string.ascii_letters + string.digits + string.punctuation


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """
    Create an instance of the default event loop for each test case.

    This fixture is used to run each test in a different async loop. Running all
    in the same loop causes errors with SQLAlchemy. See the following two issues:

    1. https://github.com/tiangolo/fastapi/issues/5692
    2. https://github.com/encode/starlette/issues/1315

    [Reference](https://tonybaloney.github.io/posts/async-test-patterns-for-pytest-and-unittest.html)
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
async def synth_engine():
    """
    Provide a fixture to prepare the test database.
    """
    engine = engine_factory.get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all, checkfirst=True)
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine_factory.cleanup()


@pytest.fixture(scope="function")
async def synth_session(synth_engine):
    """
    Get a session from the engine_factory for the current test function.

    This is necessary to make sure that the test code uses the same session as the one returned by
    the dependency injection for the router code. Otherwise, changes made in the router's session would not
    be visible in the test code. Not that changes made in this synthesized session are always rolled back
    and never committed.

    NOTE:
        Any router tests that interact with endpoints that use the database MUST use this fixture or the
        session they get will not be the same session used across different routes or by the locally bound
        services.
    """
    session = AsyncSession(synth_engine)
    await session.begin()

    @asynccontextmanager
    async def auto_session(*_, **__):
        nested_transaction = await session.begin_nested()
        try:
            yield session
            await nested_transaction.commit()
        except Exception as err:
            await nested_transaction.rollback()
            raise err

    with patch("jobbergate_api.storage.engine_factory.auto_session", new=auto_session):
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture(autouse=True, scope="session")
async def synth_s3_bucket_session():
    bucket_name = get_bucket_name()
    bucket_url = get_bucket_url()

    async with s3_bucket(bucket_name, bucket_url) as bucket:
        try:
            await bucket.create()
        except bucket.meta.client.exceptions.BucketAlreadyOwnedByYou:
            pass

        try:
            yield bucket
        finally:
            await bucket.objects.all().delete()
            await bucket.delete()


@pytest.fixture(scope="function")
async def synth_bucket(synth_s3_bucket_session):
    try:
        yield synth_s3_bucket_session
    finally:
        await synth_s3_bucket_session.objects.all().delete()


@pytest.fixture(scope="function")
async def synth_services(synth_session, synth_bucket):
    """
    Bind the session and bucket to all services.
    """
    with service_factory(synth_session, synth_bucket) as services:
        yield services


@pytest.fixture(autouse=True)
def enforce_mocked_oidc_provider(mock_openid_server):
    """
    Enforce that the OIDC provider used by armasec is the mock_openid_server provided as a fixture.

    No actual calls to an OIDC provider will be made.
    """
    yield


@pytest.fixture
def tester_email() -> str:
    """Dummy tester email."""
    return "tester@omnivector.solutions"


@pytest.fixture
async def client():
    """
    Provide a client that can issue fake requests against fastapi endpoint functions in the backend.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def inject_security_header(client, build_rs256_token):
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
        organization_id: typing.Optional[str] = None,
    ):
        claim_overrides: dict[str, typing.Any] = dict(
            email=owner_email,
            client_id=client_id,
            permissions=permissions,
            organization={organization_id: dict()},
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
        window = TimeFrame(now=datetime.datetime.utcnow() - datetime.timedelta(seconds=1), later=None)
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
        for key, value in kwargs.items():
            previous_values[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
        for key, value in previous_values.items():
            setattr(settings, key, value)

    return _helper


@pytest.fixture
def dummy_application_source_file() -> str:
    """
    Fixture to return a dummy application source file.
    """
    return dedent(
        """
        from jobbergate_cli.application_base import JobbergateApplicationBase
        from jobbergate_cli import appform

        class JobbergateApplication(JobbergateApplicationBase):

            def mainflow(self, data):
                questions = []

                questions.append(appform.List(
                    variablename="partition",
                    message="Choose slurm partition:",
                    choices=self.application_config['partitions'],
                ))

                questions.append(appform.Text(
                    variablename="job_name",
                    message="Please enter a jobname",
                    default=self.application_config['job_name']
                ))
                return questions
        """
    ).strip()


@pytest.fixture
def dummy_template() -> str:
    """
    Fixture to return a dummy template.
    """
    return dedent(
        """
        #!/bin/bash

        #SBATCH --job-name={{data.job_name}}
        #SBATCH --partition={{data.partition}}
        #SBATCH --output=sample-%j.out

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()


@pytest.fixture
def dummy_application_config() -> str:
    """
    Fixture to return a dummy application config file.
    """
    return dedent(
        """
        application_config:
            job_name: rats
            partitions:
                - debug
                - partition1
        jobbergate_config:
            default_template: test_job_script.sh
            supporting_files:
                - test_job_script.sh
            supporting_files_output_name:
                test_job_script.sh:
                    - support_file_b.py
            template_files:
                - templates/test_job_script.sh
        """
    ).strip()


@pytest.fixture
def job_script_data_as_string():
    """
    Provide a fixture that returns an example of a default application script.
    """
    content = dedent(
        """
        #!/bin/bash

        #SBATCH --job-name=rats
        #SBATCH --partition=debug
        #SBATCH --output=sample-%j.out

        # Sbatch params injected at rendering time
        #SBATCH --partition=debug
        #SBATCH --time=00:30:00

        echo $SLURM_TASKS_PER_NODE
        echo $SLURM_SUBMIT_DIR
        """
    ).strip()
    return content


@pytest.fixture
def make_dummy_file(tmp_path):
    """
    Provide a fixture that will generate a temporary file with ``size`` random bytes of text data.
    """

    def _helper(filename, size: int = 100, content: str = ""):
        """
        Auxillary function that builds the temporary file.
        """
        if not content:
            content = "".join(random.choice(CHARSET) for _ in range(size))
        dummy_path = tmp_path / filename
        dummy_path.write_text(content)
        return dummy_path

    return _helper


@pytest.fixture
def make_files_param():
    """
    Provide a fixture to use as a context manager that builds the ``files`` parameter.

    Open the supplied file(s) and build a ``files`` param appropriate for using
    multi-part file uploads with the client.
    """

    @contextlib.contextmanager
    def _helper(*file_paths):
        """
        Context manager that opens the file(s) and yields the ``files`` param from it.
        """
        with contextlib.ExitStack() as stack:
            yield [
                (
                    "upload_files",
                    (
                        path.name,
                        stack.enter_context(open(path, mode="rb")),
                        "text/plain",
                    ),
                )
                for path in file_paths
            ]

    return _helper


@pytest.fixture
def unpack_response():
    """
    Provide a callable fixture that unpacks a paginated response.

    This fixture is mostly useful for checking the response from list endpoints.

    Also:
     * assert that the response has the expected status
     * optionally extract just the value for a given key
     * optionally sort the final item list
    """

    def _helper(
        response: Response,
        expected_status_code=status.HTTP_200_OK,
        key: str | None = None,
        sort: bool = False,
        check_total: int | None = None,
        check_page: int | None = None,
        check_size: int | None = None,
        check_pages: int | None = None,
    ):
        assert response.status_code == expected_status_code, f"Request failed: {response.text}"
        response_data = response.json()
        items: list[typing.Any] = response_data.get("items", [])
        if key is not None:
            items = [i[key] for i in items]
        if sort:
            items = sorted(items)
        if check_total:
            assert response_data["total"] == check_total
        if check_page:
            assert response_data["page"] == check_page
        if check_size:
            assert response_data["size"] == check_size
        if check_pages:
            assert response_data["pages"] == check_pages
        return items

    return _helper
