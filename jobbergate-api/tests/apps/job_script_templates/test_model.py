"""Database models for the job script template resource."""
import asyncio
from contextlib import asynccontextmanager
import json

import pytest
from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy import delete, insert, join, select
from sqlalchemy.orm import joinedload, relationship, subqueryload, contains_eager

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.models import (
    JobScriptTemplate,
    JobScriptTemplateFile,
    job_script_templates_table,
    job_script_template_files_table,
)
from jobbergate_api.apps.job_script_templates.routers import job_script_template_create
from jobbergate_api.storage import database
from jobbergate_api.database import SessionLocal

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
# pytestmark = pytest.mark.usefixtures("startup_event_force")


@pytest.fixture
def get_session():
    """A fixture to return the async session used to run SQL queries against a database."""

    @asynccontextmanager
    async def _get_session():
        """Get the async session to execute queries against the database."""
        # async_session = _scoped_session()
        async with SessionLocal() as session:
            async with session.begin():
                try:
                    yield session
                except Exception as err:
                    await session.rollback()
                    raise err
                finally:
                    await session.close()

    return _get_session


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


@pytest.fixture(scope="module")
def template_values():
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        # identifier="test-identifier",
        description="test-description",
        owner_email="owner_email@test.com",
        template_vars={"output_dir": "/tmp"},
    )


@pytest.mark.asyncio
async def test_job_templates__success(template_values, time_frame):
    """
    Test that job_script_templates table is created and populated correctly.

    Note:
        For the jsonb fields is not deserialized, so we need to use json.dumps.
        This should not be a problem when combined with Pydantic models.
    """
    expected_value = JobScriptTemplate(**template_values)

    with time_frame() as window:
        insert_query = insert(JobScriptTemplate).returning(JobScriptTemplate)
        data = await database.fetch_one(query=insert_query, values=template_values)

    assert data is not None

    actual_value = JobScriptTemplate(**data._mapping)

    assert actual_value.created_at in window
    assert actual_value.updated_at in window
    assert isinstance(actual_value.id, int)

    assert actual_value.name == expected_value.name

    assert actual_value.description == expected_value.description
    assert actual_value.owner_email == expected_value.owner_email
    assert actual_value.template_vars == json.dumps(expected_value.template_vars)
    assert actual_value.files == []


@pytest.mark.asyncio
@pytest.fixture(scope="function")
async def job_script_template(get_session, template_values):
    """Return a job_script_template object."""
    template = JobScriptTemplate(**template_values)
    async with get_session() as sess:
        sess.add(template)
        await sess.commit()
        # sess.refresh(template)

        yield template


class TestJobTemplateFiles:
    @pytest.mark.asyncio
    async def test_add_files__success(self, job_script_template, time_frame):

        dummy_values = dict(
            id=job_script_template.id,
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        expected_value = JobScriptTemplateFile(**dummy_values)

        with time_frame() as window:
            insert_query = insert(JobScriptTemplateFile).returning(JobScriptTemplateFile)
            data = await database.fetch_one(query=insert_query, values=dummy_values)

        assert data is not None

        actual_value = JobScriptTemplateFile(**data._mapping)

        assert actual_value.created_at in window
        assert actual_value.updated_at in window

        assert actual_value.id == expected_value.id
        assert actual_value.filename == expected_value.filename
        assert actual_value.file_type == expected_value.file_type
        assert actual_value.file_key == "job_script_template_files/{}/{}".format(
            expected_value.id,
            expected_value.filename,
        )

    @pytest.mark.asyncio
    async def test_add_files__get_file_bundle(self, get_session, job_script_template, time_frame):

        test_files = [
            dict(
                id=job_script_template.id,
                filename="test-filename.py.j2",
                file_type=FileType.ENTRYPOINT,
            ),
            dict(
                id=job_script_template.id,
                filename="test-filename.json.j2",
                file_type=FileType.SUPPORT,
            ),
        ]

        async with get_session() as sess:

            for f in test_files:
                file = JobScriptTemplateFile(**f)
                sess.add(file)
            await sess.commit()

        async with get_session() as sess:

            query = (
                select(JobScriptTemplate)
                .options(joinedload("files"))
                .where(JobScriptTemplate.id == job_script_template.id)
            )

            data = (await sess.execute(query)).scalars().first()

        result = {**data._mapping}

        job_template = JobScriptTemplate(**data._mapping)

        assert True

    @pytest.mark.asyncio
    async def test_add_files__cascade_delete(self, template_values):

        insert_query = insert(JobScriptTemplate).returning(JobScriptTemplate)
        template_data = await database.fetch_one(query=insert_query, values=template_values)

        assert template_data is not None

        file_values = dict(
            id=template_data["id"],
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        insert_query = insert(JobScriptTemplateFile).returning(JobScriptTemplateFile)
        file_data = await database.fetch_one(query=insert_query, values=file_values)

        assert file_data is not None
        count = await database.fetch_all("SELECT COUNT(*) FROM job_script_template_files")
        assert count[0][0] == 1

        delete_query = delete(JobScriptTemplate).where(JobScriptTemplate.id == template_data["id"])
        await database.execute(query=delete_query)

        count = await database.fetch_all("SELECT COUNT(*) FROM job_script_template_files")
        assert count[0][0] == 0

    @pytest.mark.asyncio
    async def test_add_files__fail_duplicated_filename(self, job_script_template):

        dummy_values = dict(
            id=job_script_template.id,
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        insert_query = insert(JobScriptTemplateFile).returning(JobScriptTemplateFile)
        await database.fetch_one(query=insert_query, values=dummy_values)
        with pytest.raises(
            UniqueViolationError,
            match="duplicate key value violates unique constraint",
        ):
            await database.fetch_one(query=insert_query, values=dummy_values)

    @pytest.mark.asyncio
    async def test_add_files__fail_job_script_template_not_found(
        self,
        job_script_template,
    ):

        dummy_values = dict(
            id=job_script_template.id + 1,
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        insert_query = insert(JobScriptTemplateFile)
        with pytest.raises(
            ForeignKeyViolationError,
            match='insert or update on table "job_script_template_files" violates foreign key constraint',
        ):
            await database.fetch_one(query=insert_query, values=dummy_values)
