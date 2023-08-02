"""Database models for the job scripts resource."""
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect
from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_submissions.services import crud_service
from jobbergate_api.apps.job_scripts.services import crud_service as scripts_crud_service
from jobbergate_api.apps.job_scripts.services import file_service


class TestIntegration:
    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, synth_bucket):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with (
            crud_service.bound_session(synth_session),
            scripts_crud_service.bound_session(synth_session),
            file_service.bound_session(synth_session),
            file_service.bound_bucket(synth_bucket),
        ):
            yield

    async def test_get_includes_all_files(self, fill_job_script_data, fill_job_submission_data):
        script_instance = await scripts_crud_service.create(**fill_job_script_data())
        submission_instance = await crud_service.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.get(submission_instance.id, include_files=True)

        assert "job_script" not in inspect(result).unloaded
        assert "files" not in inspect(result.job_script).unloaded

        assert result.job_script.files == [script_file]

    async def test_get_includes_parent(self, fill_job_script_data, fill_job_submission_data):
        script_instance = await scripts_crud_service.create(**fill_job_script_data())
        submission_instance = await crud_service.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )

        result = await crud_service.get(submission_instance.id, include_parent=True)

        assert "job_script" not in inspect(result).unloaded
        assert "files" in inspect(result.job_script).unloaded

        assert result.job_script == script_instance

    async def test_get_not_include_parent(self, fill_job_script_data, fill_job_submission_data):
        script_instance = await scripts_crud_service.create(**fill_job_script_data())
        submission_instance = await crud_service.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )

        result = await crud_service.get(submission_instance.id, include_parent=False)

        assert "job_script" in inspect(result).unloaded

    async def test_list_includes_all_files(self, fill_job_script_data, fill_job_submission_data):
        script_instance = await scripts_crud_service.create(**fill_job_script_data())
        submission_instance = await crud_service.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        actual_result = await crud_service.list(include_files=True)

        assert actual_result == [submission_instance]
        assert actual_result[0].job_script.files == [script_file]

    async def test_update_includes_no_files(self, fill_job_script_data, fill_job_submission_data):
        script_instance = await scripts_crud_service.create(**fill_job_script_data())
        submission_instance = await crud_service.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        script_file = await file_service.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await crud_service.update(submission_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"job_script"}

        assert actual_unloaded == expected_unloaded
