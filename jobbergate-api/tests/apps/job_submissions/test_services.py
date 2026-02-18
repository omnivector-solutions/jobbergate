"""Tests for the job submission service module."""

from itertools import product
from typing import Any, NamedTuple

import pendulum
import pytest
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


class TestEntryInfo(NamedTuple):
    """Named tuple to store the info on a test entry."""

    last_updated_delta: int
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
    return {
        value["id"] for key, value in entries.items() if all(getattr(key, k) in v for k, v in kwargs.items())
    }


class TestAutoCleanUnusedJobSubmissions:
    """
    Test the clean_unused_entries method.
    """

    DAYS_TO_ARCHIVE = 1
    DAYS_TO_DELETE = 2

    @pytest.fixture
    def time_now(self):
        """
        Test fixture to freeze time for testing
        """
        time_now = pendulum.datetime(2025, 1, 1)
        with pendulum.travel_to(time_now, freeze=True):
            yield time_now

    @pytest.fixture
    async def dummy_data(
        self, fill_job_submission_data, time_now, synth_services
    ) -> dict[TestEntryInfo, dict[str, Any]]:
        """
        Create dummy test data covering a range of possible scenarios.

        The current time is pinned by pendulum, and the test data covers a range of days added to it.
        The test data is created with a range of possible values for last_updated_delta and is_archived.
        """
        result = {}

        LAST_UPDATED_DELTA_VALUES = (0, 1, 2)
        IS_ARCHIVED_VALUES = (True, False)

        for e in product(LAST_UPDATED_DELTA_VALUES, IS_ARCHIVED_VALUES):
            entry_info = TestEntryInfo(*e)
            data = fill_job_submission_data(is_archived=entry_info.is_archived)

            with pendulum.travel_to(time_now.add(days=entry_info.last_updated_delta), freeze=True):
                job_submission = await synth_services.crud.job_submission.create(**data)

            data["id"] = job_submission.id
            result[entry_info] = data

        return result

    async def test_auto_clean__unset(self, dummy_data, tweak_settings, time_now, synth_services):
        """
        Assert that nothing is deleted or archived when the thresholds are unset.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE=None,
                AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE=None,
            ),
            pendulum.travel_to(time_now.add(days=1_000), freeze=True),
        ):
            result = await synth_services.crud.job_submission.clean_unused_entries()

        assert result.archived == set()
        assert result.deleted == set()

        submissions_list = await synth_services.crud.job_submission.list()

        assert {s.id for s in submissions_list} == {s["id"] for s in dummy_data.values()}

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

        The test data is created with a range of possible values for last_updated_delta and is_archived.
        Considering the `DAYS_TO_ARCHIVE` and `DAYS_TO_DELETE` settings, we expect the following behavior:
        - On day zero, nothing should be archived or deleted.
          - Notice `set(range(0))` and `set(range(-1))` are empty sets,
            so no entries are returned by the filters.
        - On day one:
          - Entries not previously archived should be archived if last_updated_delta is 0.
          - No entries should be deleted.
        - On day two:
            - Entries not previously archived should be archived if last_updated_delta is 0 or 1.
            - Entries previously archived should be deleted if last_updated_delta is 0.
        - And so on for the following days.
        """
        with (
            tweak_settings(
                AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_ARCHIVE=self.DAYS_TO_ARCHIVE,
                AUTO_CLEAN_JOB_SUBMISSIONS_DAYS_TO_DELETE=self.DAYS_TO_DELETE,
            ),
            pendulum.travel_to(time_now.add(days=time_delta, minutes=1), freeze=True),
        ):
            result = await synth_services.crud.job_submission.clean_unused_entries()

        expected_archived_ids = filter_test_entries(
            dummy_data,
            is_archived={False},
            last_updated_delta=set(range(time_delta)),
        )
        assert result.archived == expected_archived_ids

        expected_deleted_ids = filter_test_entries(
            dummy_data,
            is_archived={True},
            last_updated_delta=set(range(time_delta - 1)),
        )
        assert result.deleted == expected_deleted_ids

        # Assert the deleted entries are not in the list of job submissions
        submissions_list = await synth_services.crud.job_submission.list()
        assert {s.id for s in submissions_list} == {s["id"] for s in dummy_data.values()} - result.deleted
