"""Database models for the job scripts resource."""
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect
from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_scripts.services import (
    crud_service,
    file_service,
)
from jobbergate_api.apps.job_script_templates.services import crud_service as template_crud_service


@pytest.fixture
def script_test_data() -> dict[str, Any]:
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        description="test-description",
        owner_email="owner_email@test.com",
    )


class TestIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, synth_bucket):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with (
            crud_service.bound_session(synth_session),
            file_service.bound_session(synth_session),
            file_service.bound_bucket(synth_bucket),
        ):
            yield

    async def test_get_includes_all_files(self, script_test_data):
        script_instance = await crud_service.create(**script_test_data)

        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.get(script_instance.id, include_files=True)

        assert "files" not in inspect(result).unloaded

        assert result.files == [script_file]

    async def test_get_includes_parent(self, script_test_data, synth_session):
        with template_crud_service.bound_session(synth_session):
            template_instance = await template_crud_service.create(
                name="test-name", identifier="test-identifier", owner_email=script_test_data["owner_email"]
            )

        script_instance = await crud_service.create(
            **script_test_data, parent_template_id=template_instance.id
        )

        actual_result = await crud_service.get(script_instance.id, include_parent=True)

        assert actual_result.template == template_instance

    async def test_get_not_include_parent(self, script_test_data, synth_session):
        with template_crud_service.bound_session(synth_session):
            template_instance = await template_crud_service.create(
                name="test-name", identifier="test-identifier", owner_email=script_test_data["owner_email"]
            )

        script_instance = await crud_service.create(
            **script_test_data, parent_template_id=template_instance.id
        )

        result = await crud_service.get(script_instance.id, include_parent=False)

        assert "template" in inspect(result).unloaded

    async def test_list_includes_all_files(self, script_test_data, synth_session):
        script_instance = await crud_service.create(**script_test_data)

        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_session.refresh(script_instance)

        actual_result = await crud_service.list(include_files=True)

        assert actual_result == [script_instance]
        assert actual_result[0].files == [script_file]

    async def test_update_includes_no_files(self, script_test_data):
        script_instance = await crud_service.create(**script_test_data)

        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.update(script_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"template", "files", "submissions"}

        assert actual_unloaded == expected_unloaded

    async def test_delete_cascades_to_files(self, script_test_data):
        script_instance = await crud_service.create(**script_test_data)

        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await crud_service.delete(script_instance.id)

        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(script_instance.id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await file_service.get(script_file.parent_id, script_file.filename)
        assert exc_info.value.status_code == 404
