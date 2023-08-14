"""Database models for the job scripts resource."""
from itertools import product
from typing import Any

import pendulum
import pytest
from fastapi import HTTPException
from sqlalchemy import inspect

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_script_templates.services import crud_service as template_crud_service
from jobbergate_api.apps.job_scripts.services import crud_service, file_service
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.services import crud_service as submission_crud_service


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
            submission_crud_service.bound_session(synth_session),
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

    async def test_delete_updates_related_submissions(self, script_test_data, fill_job_script_data):
        """
        Test all related submissions still on status CREATED are updated when parent job-script is deleted.
        """
        script_instance = await crud_service.create(**script_test_data)
        target_for_deletion = await crud_service.create(**script_test_data)

        expected_submissions = []
        for status, script in product(JobSubmissionStatus, (script_instance, target_for_deletion)):
            create_data = fill_job_script_data(
                status=status, client_id="test-client-id", job_script_id=script.id
            )
            await submission_crud_service.create(**create_data)

            # Modify on the expected results the business logic we expect to happen
            if status == JobSubmissionStatus.CREATED and script == target_for_deletion:
                create_data["status"] = JobSubmissionStatus.REJECTED
                create_data["report_message"] = "Parent job script was deleted before the submission."
            if script == target_for_deletion:
                create_data["job_script_id"] = None

            expected_submissions.append(create_data)

        await crud_service.delete(target_for_deletion.id)

        with pytest.raises(HTTPException) as exc_info:
            await crud_service.get(target_for_deletion.id)
        assert exc_info.value.status_code == 404

        actual_submissions = await submission_crud_service.list(sort_field="id", sort_ascending=True)

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

    @pytest.fixture(autouse=True)
    async def setup(self, synth_session, tweak_settings):
        """
        Ensure that the services are bound for each method in this test class.
        """
        with (
            crud_service.bound_session(synth_session),
            submission_crud_service.bound_session(synth_session),
        ):
            yield

    @pytest.fixture
    def time_now(self):
        """
        Test fixture to freeze time for testing
        """
        time_now = pendulum.datetime(2023, 1, 1)
        with pendulum.test(pendulum.datetime(2023, 1, 1)):
            yield time_now

    @pytest.fixture
    async def dummy_data(self, fill_job_script_data, fill_job_submission_data, time_now):
        """
        Create dummy test data.
        """
        result = []
        for i, is_archived in product([0, 2, 4], [True, False]):
            data = fill_job_script_data(name=f"name-{i}", is_archived=is_archived)
            with pendulum.test(time_now.add(days=i)):
                job_script = await crud_service.create(**data)
            data["id"] = job_script.id
            result.append(data)

        return result

    async def test_auto_clean__unset(self, dummy_data, tweak_settings, time_now):
        """
        Assert that nothing is deleted or archived when the thresholds are unset.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=None,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=None,
            ),
        ):
            result = await crud_service.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await crud_service.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_0(self, dummy_data, tweak_settings, time_now):
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
            result = await crud_service.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await crud_service.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_2(self, dummy_data, tweak_settings, time_now):
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
            result = await crud_service.auto_clean_unused_job_scripts()

        assert result.archived == set(s["id"] for s in dummy_data if s["is_archived"] is False)
        assert result.deleted == set()

        jobs_list = await crud_service.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}

    async def test_auto_clean__day_4(self, dummy_data, tweak_settings, time_now):
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
            result = await crud_service.auto_clean_unused_job_scripts()

        assert result.archived == set(s["id"] for s in dummy_data if s["is_archived"] is False)
        assert result.deleted == set(s["id"] for s in dummy_data if s["is_archived"] is True)

        jobs_list = await crud_service.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data} - result.deleted

    async def test_auto_clean__day_4_recently_used(
        self, dummy_data, tweak_settings, time_now, fill_job_submission_data
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
                await submission_crud_service.create(
                    **fill_job_submission_data(
                        status=JobSubmissionStatus.CREATED,
                        client_id="test-client-id",
                        job_script_id=item["id"],
                    )
                )
            result = await crud_service.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await crud_service.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data}
