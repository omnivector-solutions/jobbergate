"""Database models for the job script template resource."""
import asyncio
from contextlib import asynccontextmanager

import pytest

from jobbergate_api.apps.job_script_templates.schemas import JobTemplateCreateRequest
from jobbergate_api.apps.job_script_templates.service import create_job_script_template
from jobbergate_api.apps.models import Base
from jobbergate_api.database import SessionLocal, engine

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
# pytestmark = pytest.mark.usefixtures("startup_event_force")


@pytest.fixture(scope="session")
def get_db():
    """A fixture to return the async session used to run SQL queries against a database."""

    @asynccontextmanager
    async def _get_db():
        """Get the async session to execute queries against the database."""
        async with SessionLocal() as db:
            yield db

    return _get_db


@pytest.fixture
def tester_email() -> str:
    """Dummy tester email."""
    return "tester@omnivector.solutions"


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
async def enforce_empty_database():
    """
    Make sure our database is empty at the end of each test.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="module")
def template_values():
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        identifier="test-identifier",
        description="test-description",
        owner_email="owner_email@test.com",
        template_vars={"output_dir": "/tmp"},
    )


class TestCreateJobScriptTemplate:
    @pytest.mark.asyncio
    async def test_base_case__success(self, template_values, tester_email, get_db, time_frame):
        """Test that the template is created successfully."""

        expected_result = JobTemplateCreateRequest(**template_values)

        async with get_db() as db:
            with time_frame() as window:
                actual_result = await create_job_script_template(
                    db,
                    incoming_data=expected_result,
                    owner_email=tester_email,
                )

        assert JobTemplateCreateRequest.from_orm(actual_result) == expected_result

        assert actual_result.owner_email == tester_email
        assert actual_result.created_at in window
        assert actual_result.updated_at in window
        assert actual_result.files == []
        assert isinstance(actual_result.id, int)
