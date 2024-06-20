"""Database models for the job scripts resource."""

from itertools import product
from typing import Any, NamedTuple

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
    async def test_file_upsert__guarantee_only_one_entrypoint(
        self, file_type, script_test_data, synth_services
    ):
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

        await synth_services.file.job_script.upsert(
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

    async def test_delete_updates_related_submissions(
        self, script_test_data, fill_job_script_data, synth_services
    ):
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

        actual_submissions = await synth_services.crud.job_submission.list(
            sort_field="id", sort_ascending=True
        )

        assert [s.status for s in actual_submissions] == [s.get("status") for s in expected_submissions]

        assert [s.report_message for s in actual_submissions] == [
            s.get("report_message") for s in expected_submissions
        ]

        assert [s.job_script_id for s in actual_submissions] == [
            s.get("job_script_id") for s in expected_submissions
        ]


class TestEntryInfo(NamedTuple):
    """Named tuple to store the info on a test entry."""

    last_updated_delta: int
    last_used_delta: int | None
    is_archived: bool


def filter_test_entries(
    entries: dict[TestEntryInfo, dict[str, Any]],
    **kwargs: set[Any],
) -> set[int]:
    """
    This function returns a filter for test entries contained in a dictionary, based on specified target attributes.

    Given that entries are a dictionary of TestEntryInfo objects and their associated data,
    this function facilitates the retrieval of entry IDs that are contained in the set of values for each key in kwargs.
    """
    if not kwargs:
        return set()
    return set(
        value["id"] for key, value in entries.items() if all(getattr(key, k) in v for k, v in kwargs.items())
    )


class TestAutoCleanUnusedJobScripts:
    """
    Test the auto_clean_unused_job_scripts method.
    """

    DAYS_TO_ARCHIVE = 1
    DAYS_TO_DELETE = 2

    @pytest.fixture
    def time_now(self):
        """
        Test fixture to freeze time for testing
        """
        time_now = pendulum.datetime(2023, 1, 1)
        with pendulum.test(pendulum.datetime(2023, 1, 1)):
            yield time_now

    @pytest.fixture
    async def dummy_data(
        self, fill_job_script_data, fill_job_submission_data, time_now, synth_services
    ) -> dict[TestEntryInfo, dict[str, Any]]:
        """
        Create dummy test data covering a range of possible scenarios.

        The current time is pinned by pendulum, and the test data covers a range of days added to it.
        The test data is created with a range of possible values for last_updated_delta, last_used_delta and
        is_archived.
        Last used means the last time a job submission was created with the job script. If it is None,
        it means the job script was never used to create a job submission.
        """
        result = {}

        LAST_UPDATED_DELTA_VALUES = (0, 1, 2)
        LAST_USED_DELTA_VALUES = (None, 0, 1, 2, 3)
        IS_ARCHIVED_VALUES = (True, False)

        for e in product(LAST_UPDATED_DELTA_VALUES, LAST_USED_DELTA_VALUES, IS_ARCHIVED_VALUES):
            entry_info = TestEntryInfo(*e)
            data = fill_job_script_data(is_archived=entry_info.is_archived)

            with pendulum.test(time_now.add(days=entry_info.last_updated_delta)):
                job_script = await synth_services.crud.job_script.create(**data)

            data["id"] = job_script.id

            if entry_info.last_used_delta is not None:
                with pendulum.test(time_now.add(days=entry_info.last_used_delta)):
                    job_submission = await synth_services.crud.job_submission.create(
                        **fill_job_submission_data(
                            status=JobSubmissionStatus.CREATED,
                            client_id="test-client-id",
                            job_script_id=data["id"],
                        )
                    )
                data["child_job_submission_id"] = job_submission.id

            result[entry_info] = data

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
            pendulum.test(time_now.add(days=1_000)),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        assert result.archived == set()
        assert result.deleted == set()

        jobs_list = await synth_services.crud.job_script.list()

        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data.values()}

    @pytest.mark.parametrize("time_delta", list(range(7)))
    async def test_auto_clean__set(
        self,
        time_delta,
        dummy_data,
        tweak_settings,
        time_now,
        synth_services,
    ):
        """
        Test the expected entries are archived or deleted when advancing the current time day by day.

        The test data is created with a range of possible values for last_updated_delta, last_used_delta and
        is_archived. Considering the `DAYS_TO_ARCHIVE` and `DAYS_TO_DELETE` settings,
        we expect the following behavior:
        - On day zero, nothing should be archived or deleted.
          - Notice `set(range(0))` and `set(range(-1))` are empty sets,
            so no entries are returned by the filters.
        - On day one:
          - Entries not previously archived should be archived if last_updated_delta is 0, and
            last_used_delta is 0 or None.
          - No entries should be deleted.
        - On day two:
            - Entries not previously archived should be archived if last_updated_delta is 0 or 1, and
                last_used_delta is 0, 1, or None.
            - Entries previously archived should be deleted if last_updated_delta is 0, and last_used_delta
              is 0 or None.
        - And so on for the following days.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SCRIPTS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.test(time_now.add(days=time_delta, minutes=1)),
        ):
            result = await synth_services.crud.job_script.auto_clean_unused_job_scripts()

        expected_archived_ids = filter_test_entries(
            dummy_data,
            is_archived={False},
            last_updated_delta=set(range(time_delta)),
            last_used_delta=set(range(time_delta)) | {None},
        )
        assert result.archived == expected_archived_ids

        expected_deleted_ids = filter_test_entries(
            dummy_data,
            is_archived={True},
            last_updated_delta=set(range(time_delta - 1)),
            last_used_delta=set(range(time_delta - 1)) | {None},
        )
        assert result.deleted == expected_deleted_ids

        # Assert the deleted entries are not in the list of job scripts
        jobs_list = await synth_services.crud.job_script.list()
        assert {j.id for j in jobs_list} == {j["id"] for j in dummy_data.values()} - result.deleted
