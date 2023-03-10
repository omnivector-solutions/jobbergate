"""Database models for the job script template resource."""
import asyncio
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.exc import IntegrityError

import jobbergate_api.apps.job_script_templates.service as service
from jobbergate_api.apps.job_script_templates.schemas import (
    JobTemplateCreateRequest,
    JobTemplateUpdateRequest,
)
from jobbergate_api.apps.job_script_templates.service import (
    create_job_script_template,
    delete_job_script_template,
    read_job_script_template,
)
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
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    yield


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


class TestCreateJobScriptTemplateServices:
    @pytest.mark.asyncio
    async def test_create__success(self, template_values, tester_email, get_db, time_frame):
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

    @pytest.mark.asyncio
    async def test_create_duplicate_identifier__failure(self, template_values, tester_email, get_db):
        """Test that the template creation fails when its identifiers is not unique."""

        expected_result = JobTemplateCreateRequest(**template_values)

        expected_result.identifier = "test-identifier"

        async with get_db() as db:
            await create_job_script_template(
                db,
                incoming_data=expected_result,
                owner_email=tester_email,
            )

        async with get_db() as db:
            with pytest.raises(
                IntegrityError,
                match="duplicate key value violates unique constraint",
            ):
                await create_job_script_template(
                    db,
                    incoming_data=expected_result,
                    owner_email=tester_email,
                )

    @pytest.mark.asyncio
    async def test_count__success(self, template_values, tester_email, get_db):
        """Test that the template is created successfully."""
        local_template_values = template_values.copy()
        del local_template_values["identifier"]

        test_data = JobTemplateCreateRequest(**local_template_values)

        async with get_db() as db:
            assert await service.count(db) == 0
            for i in range(1, 4):
                await create_job_script_template(
                    db,
                    incoming_data=test_data,
                    owner_email=tester_email,
                )
                assert await service.count(db) == i

    @pytest.mark.asyncio
    async def test_read_by_id__success(self, template_values, tester_email, get_db):
        """Test that the template is read successfully."""

        incoming_data = JobTemplateCreateRequest(**template_values)

        async with get_db() as db:
            expected_result = await create_job_script_template(
                db,
                incoming_data=incoming_data,
                owner_email=tester_email,
            )

            actual_result = await read_job_script_template(db, expected_result.id)

        assert actual_result == expected_result

    @pytest.mark.asyncio
    async def test_read_by_identifier__success(self, template_values, tester_email, get_db):
        """Test that the template is read successfully."""

        incoming_data = JobTemplateCreateRequest(**template_values)

        async with get_db() as db:
            expected_result = await create_job_script_template(
                db,
                incoming_data=incoming_data,
                owner_email=tester_email,
            )

            assert expected_result.identifier is not None

            actual_result = await read_job_script_template(db, expected_result.identifier)

        assert actual_result == expected_result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("id_or_identifier", [0, "test-identifier"])
    async def test_read__id_or_identifier_not_found(self, get_db, id_or_identifier):
        """Test that the template is read successfully."""
        async with get_db() as db:
            result = await read_job_script_template(db, id_or_identifier)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete__success_by_id(self, template_values, tester_email, get_db):
        """Test that the template is read successfully."""
        incoming_data = JobTemplateCreateRequest(**template_values)

        async with get_db() as db:

            assert await service.count(db) == 0

            job_template = await create_job_script_template(
                db,
                incoming_data=incoming_data,
                owner_email=tester_email,
            )

            assert await service.count(db) == 1

            result = await read_job_script_template(db, job_template.id)
            assert result == job_template

        async with get_db() as db:
            await delete_job_script_template(db, job_template.id)
            assert await service.count(db) == 0
            result = await read_job_script_template(db, job_template.id)
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("id_or_identifier", [0, "test-identifier"])
    async def test_delete__id_or_identifier_not_found(self, get_db, id_or_identifier):
        """Test that the template is deleted successfully."""
        async with get_db() as db:
            await delete_job_script_template(db, id_or_identifier)

    @pytest.mark.asyncio
    async def test_update(self, template_values, tester_email, get_db):
        """Test that the template is updated successfully."""
        incoming_data = JobTemplateCreateRequest(**template_values)

        expected_data = JobTemplateUpdateRequest(
            name="new-name",
            identifier="new-identifier",
            description=None,
            template_vars={"new_output_dir": "/tmp"},
        )

        async with get_db() as db:
            initial_data = await create_job_script_template(
                db,
                incoming_data=incoming_data,
                owner_email=tester_email,
            )

        assert JobTemplateUpdateRequest.from_orm(initial_data) != expected_data

        async with get_db() as db:
            actual_data = await service.update(
                db,
                initial_data.id,
                incoming_data=expected_data,
            )

        assert JobTemplateUpdateRequest.from_orm(actual_data) == expected_data
