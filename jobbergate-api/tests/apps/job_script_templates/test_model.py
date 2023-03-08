"""Database models for the job script template resource."""
import json

import pytest
from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from sqlalchemy import delete, insert

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.models import JobScriptTemplate, JobScriptTemplateFiles
from jobbergate_api.storage import database

# Force the async event loop at the app to begin.
# Since this is a time consuming fixture, it is just used where strict necessary.
pytestmark = pytest.mark.usefixtures("startup_event_force")


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
async def job_script_template(template_values):
    """Return a job_script_template object."""
    insert_query = insert(JobScriptTemplate).returning(JobScriptTemplate)
    data = await database.fetch_one(query=insert_query, values=template_values)

    assert data is not None

    job_template = JobScriptTemplate(**data._mapping)

    yield job_template


class TestJobTemplateFiles:
    @pytest.mark.asyncio
    async def test_add_files__success(self, job_script_template, time_frame):

        dummy_values = dict(
            id=job_script_template.id,
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        expected_value = JobScriptTemplateFiles(**dummy_values)

        with time_frame() as window:
            insert_query = insert(JobScriptTemplateFiles).returning(JobScriptTemplateFiles)
            data = await database.fetch_one(query=insert_query, values=dummy_values)

        assert data is not None

        actual_value = JobScriptTemplateFiles(**data._mapping)

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
    async def test_add_files__cascade_delete(self, template_values):

        insert_query = insert(JobScriptTemplate).returning(JobScriptTemplate)
        template_data = await database.fetch_one(query=insert_query, values=template_values)

        assert template_data is not None

        file_values = dict(
            id=template_data["id"],
            filename="test-filename.j2",
            file_type=FileType.ENTRYPOINT,
        )

        insert_query = insert(JobScriptTemplateFiles).returning(JobScriptTemplateFiles)
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

        insert_query = insert(JobScriptTemplateFiles).returning(JobScriptTemplateFiles)
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

        insert_query = insert(JobScriptTemplateFiles)
        with pytest.raises(
            ForeignKeyViolationError,
            match='insert or update on table "job_script_template_files" violates foreign key constraint',
        ):
            await database.fetch_one(query=insert_query, values=dummy_values)
