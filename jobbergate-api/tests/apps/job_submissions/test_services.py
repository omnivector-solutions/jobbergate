"""Database models for the job scripts resource."""

from sqlalchemy import inspect

from jobbergate_api.apps.constants import FileType


class TestIntegration:
    async def test_get_includes_all_files(
        self, fill_job_script_data, fill_job_submission_data, synth_services
    ):
        script_instance = await synth_services.crud.job_script.create(**fill_job_script_data())
        submission_instance = await synth_services.crud.job_submission.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.job_submission.get(submission_instance.id, include_files=True)

        assert "job_script" not in inspect(result).unloaded
        assert "files" not in inspect(result.job_script).unloaded

        assert result.job_script.files == [script_file]

    async def test_get_includes_parent(self, fill_job_script_data, fill_job_submission_data, synth_services):
        script_instance = await synth_services.crud.job_script.create(**fill_job_script_data())
        submission_instance = await synth_services.crud.job_submission.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )

        result = await synth_services.crud.job_submission.get(submission_instance.id, include_parent=True)

        assert "job_script" not in inspect(result).unloaded
        assert "files" in inspect(result.job_script).unloaded

        assert result.job_script == script_instance

    async def test_get_not_include_parent(
        self, fill_job_script_data, fill_job_submission_data, synth_services
    ):
        script_instance = await synth_services.crud.job_script.create(**fill_job_script_data())
        submission_instance = await synth_services.crud.job_submission.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )

        result = await synth_services.crud.job_submission.get(submission_instance.id, include_parent=False)

        assert "job_script" in inspect(result).unloaded

    async def test_list_includes_all_files(
        self, fill_job_script_data, fill_job_submission_data, synth_services
    ):
        script_instance = await synth_services.crud.job_script.create(**fill_job_script_data())
        submission_instance = await synth_services.crud.job_submission.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        actual_result = await synth_services.crud.job_submission.list(include_files=True)

        assert actual_result == [submission_instance]
        assert actual_result[0].job_script.files == [script_file]

    async def test_update_includes_no_files(
        self, fill_job_script_data, fill_job_submission_data, synth_services
    ):
        script_instance = await synth_services.crud.job_script.create(**fill_job_script_data())
        submission_instance = await synth_services.crud.job_submission.create(
            **fill_job_submission_data(), job_script_id=script_instance.id
        )
        await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.job_submission.update(submission_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"job_script", "metrics", "progress_entries"}

        assert actual_unloaded == expected_unloaded
