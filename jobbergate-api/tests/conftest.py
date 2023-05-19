"""Configuration of pytest."""
import asyncio
import contextlib
import dataclasses
import datetime
import random
import string
import typing
from textwrap import dedent

import pytest
from httpx import AsyncClient

from jobbergate_api.apps.models import Base
from jobbergate_api.config import settings
from jobbergate_api.database import engine
from jobbergate_api.main import app

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


@pytest.fixture(scope="function")
async def database():
    """
    Create a new database connection and transaction for each test.
    """
    conn = await engine.connect()
    txn = await conn.begin()
    yield conn
    await txn.rollback()
    await conn.close()


@pytest.fixture(autouse=True, scope="function")
async def enforce_empty_database():
    """
    Make sure our database is empty at the end of each test.

    Notes:
        The order is important when deleting tables given that some tables have foreign keys.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


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
        for (key, value) in kwargs.items():
            previous_values[key] = getattr(settings, key)
            setattr(settings, key, value)
        yield
        for (key, value) in previous_values.items():
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
            output_directory: .
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