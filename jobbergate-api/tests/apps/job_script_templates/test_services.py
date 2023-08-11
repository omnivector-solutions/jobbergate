"""Database models for the smart template resource."""
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect
from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME
from jobbergate_api.apps.job_script_templates.services import (
    crud_service,
    template_file_service,
    workflow_file_service,
)


@pytest.fixture
def template_test_data() -> dict[str, Any]:
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        identifier="test-identifier",
        description="test-description",
        owner_email="owner_email@test.com",
        template_vars={"output_dir": "/tmp"},
    )


class TestJobScriptTemplateCrudService:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session):
        """
        Ensure that the crud service is bound for each method in this test class.
        """
        with crud_service.bound_session(synth_session):
            yield crud_service

    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_get__success(self, locator_attribute, template_test_data):
        """Test that the template is recovered successfully using multiple locator attributes."""

        instance = await crud_service.create(**template_test_data)
        locator = getattr(instance, locator_attribute)
        assert await crud_service.get(locator) == instance

    @pytest.mark.parametrize("identifier", ("", " ", "10"))
    async def test_create__invalid_identifier(self, identifier, template_test_data):
        """Test that the template is not created with an invalid identifier."""
        template_test_data["identifier"] = identifier
        with pytest.raises(HTTPException) as exc_info:
            await crud_service.create(**template_test_data)
        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize("identifier", ("", " ", "10"))
    async def test_update__invalid_identifier(self, identifier, template_test_data):
        """Test that the template is not updated with an invalid identifier."""
        instance = await crud_service.create(**template_test_data)
        with pytest.raises(HTTPException) as exc_info:
            await crud_service.update(instance.id, identifier=identifier)
        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_delete__success(
        self,
        locator_attribute,
        template_test_data,
    ):
        """Test that the template is deleted successfully using multiple locator attributes."""
        instance = await crud_service.create(**template_test_data)
        locator = getattr(instance, locator_attribute)
        assert await crud_service.count() == 1
        assert await crud_service.get(locator) == instance

        await crud_service.delete(locator)
        assert await crud_service.count() == 0

        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(locator)
        assert exc_info.value.status_code == 404

    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_update__success(self, locator_attribute, template_test_data):
        """Test that the template is updated successfully."""
        instance = await crud_service.create(**template_test_data)
        locator = getattr(instance, locator_attribute)

        update_data = dict(
            name="new-name",
            identifier="new-identifier",
            description=None,
            template_vars={"new_output_dir": "/tmp"},
        )

        assert instance.name != "new-name"
        assert instance.identifier != "new-identifier"

        updated_instance = await crud_service.update(locator, **update_data)
        assert updated_instance.id == instance.id
        assert updated_instance.name == "new-name"
        assert updated_instance.identifier == "new-identifier"
        assert updated_instance.description is None
        assert updated_instance.template_vars == {"new_output_dir": "/tmp"}

    @pytest.mark.parametrize("has_identifier", (True, False))
    async def test_get__omit_null_identifiers(self, has_identifier, template_test_data):
        """Test that the template is updated successfully."""
        if not has_identifier:
            del template_test_data["identifier"]
        instance = await crud_service.create(**template_test_data)

        assert await crud_service.list() == [instance]
        if not has_identifier:
            assert await crud_service.list(include_null_identifier=False) == []
        else:
            assert await crud_service.list(include_null_identifier=False) == [instance]


class TestTemplateFilesService:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, synth_bucket):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with template_file_service.bound_session(synth_session):
            with template_file_service.bound_bucket(synth_bucket):
                with crud_service.bound_session(synth_session):
                    yield

    async def test_upsert(self, template_test_data):
        """
        Test that the ``upsert()`` method functions correctly.

        Additionally, test that the database rows include the "filename" and "file_type" attributes.
        Also test that when the job script template instance is deleted, the corresponding
        job script template file instance is deleted.
        """
        template_instance = await crud_service.create(**template_test_data)
        assert template_instance is not None

        # Will this create if we don't have a corresponding job_script_template?
        template_file = await template_file_service.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        assert template_file.parent_id == template_instance.id
        assert template_file.filename == "test.txt"
        assert template_file.file_type == FileType.ENTRYPOINT
        assert template_file.file_key.endswith("test.txt")

        file_content = await template_file_service.get_file_content(template_file)
        assert file_content == "test file content".encode()

        await crud_service.delete(template_instance.id)
        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(template_instance.id)
        assert exc_info.value.status_code == 404
        assert await template_file_service.find_children(template_instance.id) == []


class TestWorkflowFilesService:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, synth_bucket):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with workflow_file_service.bound_session(synth_session):
            with workflow_file_service.bound_bucket(synth_bucket):
                with crud_service.bound_session(synth_session):
                    yield

    async def test_upsert(self, template_test_data):
        """
        Test that the ``upsert()`` method functions correctly.

        Additionally, test that the database rows include the "filename" and "file_type" attributes.
        Also test that when the job script template instance is deleted, the corresponding
        workflow file instance is deleted.
        """
        template_instance = await crud_service.create(**template_test_data)
        assert template_instance is not None

        # Will this create if we don't have a corresponding job_script_template?
        workflow_file = await workflow_file_service.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "test file content",
            runtime_config=dict(foo="bar"),
        )

        assert workflow_file.parent_id == template_instance.id
        assert workflow_file.filename == WORKFLOW_FILE_NAME
        assert workflow_file.runtime_config == dict(foo="bar")
        assert workflow_file.file_key.endswith(WORKFLOW_FILE_NAME)

        file_content = await workflow_file_service.get_file_content(workflow_file)
        assert file_content == "test file content".encode()

        await crud_service.delete(template_instance.id)
        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(template_instance.id)
        assert exc_info.value.status_code == 404
        assert await workflow_file_service.find_children(template_instance.id) == []


class TestIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, synth_bucket):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with (
            crud_service.bound_session(synth_session),
            workflow_file_service.bound_session(synth_session),
            workflow_file_service.bound_bucket(synth_bucket),
            template_file_service.bound_session(synth_session),
            template_file_service.bound_bucket(synth_bucket),
        ):
            yield

    async def test_get_template_includes_all_files(self, template_test_data):
        template_instance = await crud_service.create(**template_test_data)

        workflow_file = await workflow_file_service.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "test file content",
            runtime_config=dict(foo="bar"),
        )

        template_file = await template_file_service.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.get(template_instance.id, include_files=True)

        assert {"workflow_files", "template_files"} not in inspect(result).unloaded

        assert result.workflow_files == [workflow_file]
        assert result.template_files == [template_file]

    async def test_list_template_includes_all_files(self, template_test_data, synth_session):
        template_instance = await crud_service.create(**template_test_data)

        workflow_file = await workflow_file_service.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "test file content",
            runtime_config=dict(foo="bar"),
        )

        template_file = await template_file_service.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_session.refresh(template_instance)

        actual_result = await crud_service.list(include_files=True)

        assert actual_result == [template_instance]
        assert actual_result[0].workflow_files == [workflow_file]
        assert actual_result[0].template_files == [template_file]

    async def test_update_template_includes_no_files(self, template_test_data):
        template_instance = await crud_service.create(**template_test_data)

        workflow_file = await workflow_file_service.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "test file content",
            runtime_config=dict(foo="bar"),
        )

        template_file = await template_file_service.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.update(template_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"workflow_files", "scripts", "template_files"}

        assert actual_unloaded == expected_unloaded

    async def test_delete_cascades_to_files(self, template_test_data):
        template_instance = await crud_service.create(**template_test_data)

        workflow_file = await workflow_file_service.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "test file content",
            runtime_config=dict(foo="bar"),
        )

        template_file = await template_file_service.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await crud_service.delete(template_instance.id)

        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(template_instance.id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await workflow_file_service.get(workflow_file.parent_id, workflow_file.filename)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await template_file_service.get(template_file.parent_id, template_file.filename)
        assert exc_info.value.status_code == 404
