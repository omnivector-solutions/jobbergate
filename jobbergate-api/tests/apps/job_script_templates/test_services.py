"""Database models for the smart template resource."""

from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.constants import WORKFLOW_FILE_NAME


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
    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_get__success(self, locator_attribute, template_test_data, synth_services):
        """Test that the template is recovered successfully using multiple locator attributes."""

        instance = await synth_services.crud.template.create(**template_test_data)
        locator = getattr(instance, locator_attribute)
        assert await synth_services.crud.template.get(locator) == instance

    @pytest.mark.parametrize("identifier", ("", " ", "10"))
    async def test_create__invalid_identifier(self, identifier, template_test_data, synth_services):
        """Test that the template is not created with an invalid identifier."""
        template_test_data["identifier"] = identifier
        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.create(**template_test_data)
        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize("identifier", ("", " ", "10"))
    async def test_update__invalid_identifier(self, identifier, template_test_data, synth_services):
        """Test that the template is not updated with an invalid identifier."""
        instance = await synth_services.crud.template.create(**template_test_data)
        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.update(instance.id, identifier=identifier)
        assert exc_info.value.status_code == 422

    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_delete__success(
        self,
        locator_attribute,
        template_test_data,
        synth_services,
    ):
        """Test that the template is deleted successfully using multiple locator attributes."""
        instance = await synth_services.crud.template.create(**template_test_data)
        locator = getattr(instance, locator_attribute)
        assert await synth_services.crud.template.count() == 1
        assert await synth_services.crud.template.get(locator) == instance

        await synth_services.crud.template.delete(locator)
        assert await synth_services.crud.template.count() == 0

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.get(locator)
        assert exc_info.value.status_code == 404

    @pytest.mark.parametrize("locator_attribute", ("id", "identifier"))
    async def test_update__success(self, locator_attribute, template_test_data, synth_services):
        """Test that the template is updated successfully."""
        instance = await synth_services.crud.template.create(**template_test_data)
        locator = getattr(instance, locator_attribute)

        update_data = dict(
            name="new-name",
            identifier="new-identifier",
            description=None,
            template_vars={"new_output_dir": "/tmp"},
        )

        assert instance.name != "new-name"
        assert instance.identifier != "new-identifier"

        updated_instance = await synth_services.crud.template.update(locator, **update_data)
        assert updated_instance.id == instance.id
        assert updated_instance.name == "new-name"
        assert updated_instance.identifier == "new-identifier"
        assert updated_instance.description is None
        assert updated_instance.template_vars == {"new_output_dir": "/tmp"}

    @pytest.mark.parametrize("has_identifier", (True, False))
    async def test_get__omit_null_identifiers(self, has_identifier, template_test_data, synth_services):
        """Test that the template is updated successfully."""
        if not has_identifier:
            del template_test_data["identifier"]
        instance = await synth_services.crud.template.create(**template_test_data)

        assert await synth_services.crud.template.list() == [instance]
        if not has_identifier:
            assert await synth_services.crud.template.list(include_null_identifier=False) == []
        else:
            assert await synth_services.crud.template.list(include_null_identifier=False) == [instance]


class TestTemplateFilesService:
    async def test_upsert(self, template_test_data, synth_services):
        """
        Test that the ``upsert()`` method functions correctly.

        Additionally, test that the database rows include the "filename" and "file_type" attributes.
        Also test that when the job script template instance is deleted, the corresponding
        job script template file instance is deleted.
        """
        template_instance = await synth_services.crud.template.create(**template_test_data)
        assert template_instance is not None

        # Will this create if we don't have a corresponding job_script_template?
        template_file = await synth_services.file.template.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        assert template_file.parent_id == template_instance.id
        assert template_file.filename == "test.txt"
        assert template_file.file_type == FileType.ENTRYPOINT
        assert template_file.file_key.endswith("test.txt")

        file_content = await synth_services.file.template.get_file_content(template_file)
        assert file_content == "test file content".encode()

        await synth_services.crud.template.delete(template_instance.id)
        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.get(template_instance.id)
        assert exc_info.value.status_code == 404
        assert await synth_services.file.template.find_children(template_instance.id) == []


class TestWorkflowFilesService:
    async def test_upsert(self, template_test_data, synth_services):
        """
        Test that the ``upsert()`` method functions correctly.

        Additionally, test that the database rows include the "filename" and "file_type" attributes.
        Also test that when the job script template instance is deleted, the corresponding
        workflow file instance is deleted.
        """
        template_instance = await synth_services.crud.template.create(**template_test_data)
        assert template_instance is not None

        # Will this create if we don't have a corresponding job_script_template?
        workflow_file = await synth_services.file.workflow.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "print('hello world')",
            runtime_config=dict(foo="bar"),
        )

        assert workflow_file.parent_id == template_instance.id
        assert workflow_file.filename == WORKFLOW_FILE_NAME
        assert workflow_file.runtime_config == dict(foo="bar")
        assert workflow_file.file_key.endswith(WORKFLOW_FILE_NAME)

        file_content = await synth_services.file.workflow.get_file_content(workflow_file)
        assert file_content == "print('hello world')".encode()

        await synth_services.crud.template.delete(template_instance.id)
        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.get(template_instance.id)
        assert exc_info.value.status_code == 404
        assert await synth_services.file.workflow.find_children(template_instance.id) == []


class TestIntegration:
    async def test_get_template_includes_all_files(self, template_test_data, synth_services):
        template_instance = await synth_services.crud.template.create(**template_test_data)

        workflow_file = await synth_services.file.workflow.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "print('hello world')",
            runtime_config=dict(foo="bar"),
        )

        template_file = await synth_services.file.template.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.template.get(template_instance.id, include_files=True)

        assert {"workflow_files", "template_files"} not in inspect(result).unloaded

        assert result.workflow_files == [workflow_file]
        assert result.template_files == [template_file]

    async def test_list_template_includes_all_files(self, template_test_data, synth_session, synth_services):
        template_instance = await synth_services.crud.template.create(**template_test_data)

        workflow_file = await synth_services.file.workflow.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "print('hello world')",
            runtime_config=dict(foo="bar"),
        )

        template_file = await synth_services.file.template.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_session.refresh(template_instance)

        actual_result = await synth_services.crud.template.list(include_files=True)

        assert actual_result == [template_instance]
        assert actual_result[0].workflow_files == [workflow_file]
        assert actual_result[0].template_files == [template_file]

    async def test_update_template_includes_no_files(self, template_test_data, synth_services):
        template_instance = await synth_services.crud.template.create(**template_test_data)

        await synth_services.file.workflow.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "print('hello world')",
            runtime_config=dict(foo="bar"),
        )

        await synth_services.file.template.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.template.update(template_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"workflow_files", "scripts", "template_files"}

        assert actual_unloaded == expected_unloaded

    async def test_delete_cascades_to_files(self, template_test_data, synth_services):
        template_instance = await synth_services.crud.template.create(**template_test_data)

        workflow_file = await synth_services.file.workflow.upsert(
            template_instance.id,
            WORKFLOW_FILE_NAME,
            "print('hello world')",
            runtime_config=dict(foo="bar"),
        )

        template_file = await synth_services.file.template.upsert(
            template_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_services.crud.template.delete(template_instance.id)

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.template.get(template_instance.id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.file.workflow.get(workflow_file.parent_id, workflow_file.filename)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.file.template.get(template_file.parent_id, template_file.filename)
        assert exc_info.value.status_code == 404
