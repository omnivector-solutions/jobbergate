"""Database models for the job scripts resource."""
from itertools import product
from typing import Any

import pendulum
import pytest
from fastapi import HTTPException
from sqlalchemy import inspect

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus


@pytest.fixture
def script_test_data() -> dict[str, Any]:
    """Return a dictionary with dummy values."""
    return dict(
        name="test-name",
        description="test-description",
        owner_email="owner_email@test.com",
    )


class TestIntegration:
    @pytest.mark.parametrize("file_type", [FileType.ENTRYPOINT, FileType.ENTRYPOINT.value])
    async def test_file_upsert__guarantee_only_one_entrypoint(self, file_type, script_test_data, synth_services):
        """
        Ensure that only one entrypoint file is allowed.
        """
        script_instance = await synth_services.crud.job_script.create(**script_test_data)

        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=file_type,
        )

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.file.job_script.upsert(
                script_file.parent_id,
                "another_test.txt",
                "another test file content",
                file_type=file_type,
            )
        assert exc_info.value.status_code == 422
        assert "more than one entry point file" in exc_info.value.detail

    async def test_get_includes_all_files(self, script_test_data, synth_services):
        script_instance = await synth_services.crud.job_script.create(**script_test_data)

        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.job_script.get(script_instance.id, include_files=True)

        assert "files" not in inspect(result).unloaded

        assert result.files == [script_file]

    async def test_get_includes_parent(self, script_test_data, synth_services):
        template_instance = await synth_services.crud.template.create(
            name="test-name", identifier="test-identifier", owner_email=script_test_data["owner_email"]
        )

        script_instance = await synth_services.crud.job_script.create(
            **script_test_data, parent_template_id=template_instance.id
        )

        actual_result = await synth_services.crud.job_script.get(script_instance.id, include_parent=True)

        assert actual_result.template == template_instance

    async def test_get_not_include_parent(self, script_test_data, synth_services):
        template_instance = await synth_services.crud.template.create(
            name="test-name", identifier="test-identifier", owner_email=script_test_data["owner_email"]
        )

        script_instance = await synth_services.crud.job_script.create(
            **script_test_data, parent_template_id=template_instance.id
        )

        result = await synth_services.crud.job_script.get(script_instance.id, include_parent=False)

        assert "template" in inspect(result).unloaded

    async def test_list_includes_all_files(self, script_test_data, synth_session, synth_services):
        script_instance = await synth_services.crud.job_script.create(**script_test_data)

        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_session.refresh(script_instance)

        actual_result = await synth_services.crud.job_script.list(include_files=True)

        assert actual_result == [script_instance]
        assert actual_result[0].files == [script_file]

    async def test_update_includes_no_files(self, script_test_data, synth_services):
        script_instance = await synth_services.crud.job_script.create(**script_test_data)

        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        result = await synth_services.crud.job_script.update(script_instance.id, name="new-name")

        actual_unloaded = inspect(result).unloaded
        expected_unloaded = {"template", "files", "submissions"}

        assert actual_unloaded == expected_unloaded

    async def test_delete_cascades_to_files(self, script_test_data, synth_services):
        script_instance = await synth_services.crud.job_script.create(**script_test_data)

        script_file = await synth_services.file.job_script.upsert(
            script_instance.id,
            "test.txt",
            "test file content",
            file_type=FileType.ENTRYPOINT,
        )

        await synth_services.crud.job_script.delete(script_instance.id)

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.job_script.get(script_instance.id)
        assert exc_info.value.status_code == 404

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.file.job_script.get(script_file.parent_id, script_file.filename)
        assert exc_info.value.status_code == 404

    async def test_delete_updates_related_submissions(self, script_test_data, fill_job_script_data, synth_services):
        """
        Test all related submissions still on status CREATED are updated when parent job-script is deleted.
        """
        script_instance = await synth_services.crud.job_script.create(**script_test_data)
        target_for_deletion = await synth_services.crud.job_script.create(**script_test_data)

        expected_submissions = []
        for status, script in product(JobSubmissionStatus, (script_instance, target_for_deletion)):
            create_data = fill_job_script_data(
                status=status, client_id="test-client-id", job_script_id=script.id
            )
            await synth_services.crud.job_submission.create(**create_data)

            # Modify on the expected results the business logic we expect to happen
            if status == JobSubmissionStatus.CREATED and script == target_for_deletion:
                create_data["status"] = JobSubmissionStatus.REJECTED
                create_data["report_message"] = "Parent job script was deleted before the submission."
            if script == target_for_deletion:
                create_data["job_script_id"] = None

            expected_submissions.append(create_data)

        await synth_services.crud.job_script.delete(target_for_deletion.id)

        with pytest.raises(HTTPException) as exc_info:
            await synth_services.crud.job_script.get(target_for_deletion.id)
        assert exc_info.value.status_code == 404

        actual_submissions = await synth_services.crud.job_submission.list(sort_field="id", sort_ascending=True)

        assert [s.status for s in actual_submissions] == [s.get("status") for s in expected_submissions]

        assert [s.report_message for s in actual_submissions] == [
            s.get("report_message") for s in expected_submissions
        ]

        assert [s.job_script_id for s in actual_submissions] == [
            s.get("job_script_id") for s in expected_submissions
        ]


class TestAutoCleanUnusedJobScripts:
    """
    Test the auto_clean_unused_job_scripts method.
    """

    DAYS_TO_ARCHIVE = 1
    DAYS_TO_DELETE = 3

    @pytest.fixture
    def time_now(self):
        """
        Test fixture to freeze time for testing
        """
        time_now = pendulum.datetime(2023, 1, 1)
        with pendulum.test(pendulum.datetime(2023, 1, 1)):
            yield time_now

    @pytest.fixture
    async def dummy_data(self, fill_job_script_data, time_now, synth_services):
        """
        Create dummy test data.
        """
        result = []
        for i, is_archived in product([0, 2, 4], [True, False]):
            data = fill_job_script_data(name=f"name-{i}", is_archived=is_archived)
            with pendulum.test(time_now.add(days=i)):
                job_script = await synth_services.crud.job_script.create(**data)
            data["id"] = job_script.id
            result.append(data)

        return result

    async def test_auto_clean__unset(self, dummy_data, tweak_settings, time_now, synth_services):
        """
        Assert that nothing is deleted or archived when the thresholds are unset.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=None,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=None,
            ),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_0(self, dummy_data, tweak_settings, time_now, synth_services):
        """
        Test that nothing is deleted or archived on day 0, because the conditions are not met.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.test(time_now),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_2(self, dummy_data, tweak_settings, time_now, synth_services):
        """
        Test that not archived job scripts are archived on day 2, but nothing is deleted.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.test(time_now.add(days=2)),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set(s["id"] for s in dummy_data if s["is_archived"] is False)
        assert result.deleted == set()

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_4(self, dummy_data, tweak_settings, time_now, synth_services):
        """
        Test that not archived job script are archived, while archived job scripts are deleted.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.test(time_now.add(days=4)),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set(s["id"] for s in dummy_data if s["is_archived"] is False)
        assert result.deleted == set(s["id"] for s in dummy_data if s["is_archived"] is True)

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data} - result.deleted

    async def test_auto_clean__day_4_recently_used(
        self, dummy_data, tweak_settings, time_now, fill_job_submission_data, synth_services
    ):
        """
        Test that nothing is deleted or archived on day 4, because all of them have a recent job submission.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.test(time_now.add(days=4)),
        ):
            for item in dummy_data:
                await synth_services.crud.job_submission.create(
                    **fill_job_submission_data(
                        status=JobSubmissionStatus.CREATED,
                        client_id="test-client-id",
                        job_script_id=item["id"],
                    )
                )
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}
