from unittest import mock

import pytest
import respx
from httpx import Response, codes
from polyfactory.factories.pydantic_factory import ModelFactory

from jobbergate_core.sdk.job_submissions.app import JobSubmissions
from jobbergate_core.sdk.job_submissions.constants import JobSubmissionStatus
from jobbergate_core.sdk.job_submissions.schemas import JobSubmissionDetailedView, JobSubmissionListView
from jobbergate_core.sdk.schemas import PydanticDateTime
from jobbergate_core.sdk.utils import filter_null_out
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"

ModelFactory.add_provider(PydanticDateTime, lambda: ModelFactory.__faker__.date_time())


class JobSubmissionDetailedViewFactory(ModelFactory[JobSubmissionDetailedView]):
    """Factory for generating test data based on JobSubmissionDetailedView objects."""

    __model__ = JobSubmissionDetailedView


class JobSubmissionListViewFactory(ModelFactory[JobSubmissionListView]):
    """Factory for generating test data based on JobSubmissionListView objects."""

    __model__ = JobSubmissionListView


class TestJobSubmissions:
    job_submissions = JobSubmissions(client=Client(base_url=BASE_URL))

    def test_create(self, faker) -> None:
        """Test the create method of JobSubmissions."""
        response_data = JobSubmissionDetailedViewFactory.build(job_script_id=faker.random_int())
        create_kwargs = filter_null_out(
            {
                "job_script_id": response_data.job_script_id,
                "name": response_data.name,
                "description": response_data.description,
                "execution_directory": response_data.execution_directory,
                "client_id": response_data.client_id,
            }
        )

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.post(
                "/jobbergate/job-submissions",
                data=create_kwargs,
            ).mock(return_value=Response(codes.CREATED, content=response_data.model_dump_json()))

            result = self.job_submissions.create(**create_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_create_request_error(self, faker) -> None:
        """Test the create method of JobSubmissions with a request error."""
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.post("/jobbergate/job-submissions").mock(
                return_value=Response(codes.INTERNAL_SERVER_ERROR)
            )
            self.job_submissions.create(job_script_id=faker.random_int(), name=faker.word())

        assert route.call_count == 1

    def test_clone(self, faker) -> None:
        """Test the clone method of JobSubmissions."""
        response_data = JobSubmissionDetailedViewFactory.build()
        job_submission_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.post(f"/jobbergate/job-submissions/clone/{job_submission_id}").mock(
                return_value=Response(codes.CREATED, content=response_data.model_dump_json())
            )

            result = self.job_submissions.clone(job_submission_id)

        assert route.call_count == 1
        assert result == response_data

    def test_get_one(self) -> None:
        """Test the get_one method of JobSubmissions."""
        response_data = JobSubmissionDetailedViewFactory.build()
        job_submission_id = response_data.id

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            result = self.job_submissions.get_one(job_submission_id)

        assert route.call_count == 1
        assert result == response_data

    def test_list(self, faker, wrap_items_on_paged_response) -> None:
        """Test the list method of JobSubmissions."""
        size = 5
        response_data = wrap_items_on_paged_response(JobSubmissionListViewFactory.batch(size))
        list_kwargs = {
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": size,
            "page": faker.random_int(),
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get("/jobbergate/job-submissions", params=list_kwargs).mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            result = self.job_submissions.get_list(**list_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_update(self, faker) -> None:
        """Test the update method of JobSubmissions."""
        response_data = JobSubmissionDetailedViewFactory.build()
        job_submission_id = response_data.id
        update_kwargs = {
            "name": faker.word(),
            "description": faker.sentence(),
            "execution_directory": faker.file_path(),
        }

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(
                f"/jobbergate/job-submissions/{job_submission_id}",
                data=update_kwargs,
            ).mock(return_value=Response(codes.OK, content=response_data.model_dump_json()))

            result = self.job_submissions.update(job_submission_id, **update_kwargs)

        assert route.call_count == 1
        assert result == response_data

    def test_delete(self, faker) -> None:
        """Test the delete method of JobSubmissions."""
        job_submission_id = faker.random_int()

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.delete(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(codes.NO_CONTENT)
            )

            self.job_submissions.delete(job_submission_id)

        assert route.call_count == 1

    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id(self, mocked_sleep, faker) -> None:
        """Test the get_one_ensure_slurm_id method of JobSubmissions (happy path)."""
        response_data = JobSubmissionDetailedViewFactory.build(slurm_job_id=faker.random_int())
        job_submission_id = response_data.id

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.get(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(200, content=response_data.model_dump_json())
            )
            result = self.job_submissions.get_one_ensure_slurm_id(job_submission_id, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1
        assert result == response_data

    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_rejected_status(self, mocked_sleep) -> None:
        """Test the get_one_ensure_slurm_id method when the job submission is rejected."""
        response_data = JobSubmissionDetailedViewFactory.build(status=JobSubmissionStatus.REJECTED, slurm_job_id=None)
        job_submission_id = response_data.id

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(ValueError, match="was rejected and does not have a SLURM job ID"),
        ):
            route = respx_mock.get(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            self.job_submissions.get_one_ensure_slurm_id(job_submission_id, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1

    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_timeout(self, mocked_sleep) -> None:
        """Test the get_one_ensure_slurm_id method when SLURM job ID is not set within retries."""
        response_data = JobSubmissionDetailedViewFactory.build(slurm_job_id=None, status=JobSubmissionStatus.CREATED)
        job_submission_id = response_data.id

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(TimeoutError, match="was not set within 3 retry attempts"),
        ):
            route = respx_mock.get(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )
            self.job_submissions.get_one_ensure_slurm_id(job_submission_id, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 2
        assert route.call_count == 3

    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_request_error(self, mocked_sleep, faker) -> None:
        """Test the get_one_ensure_slurm_id method when a request error occurs."""
        job_submission_id = faker.random_int()
        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.get(f"/jobbergate/job-submissions/{job_submission_id}").mock(
                return_value=Response(codes.BAD_REQUEST)
            )
            self.job_submissions.get_one_ensure_slurm_id(job_submission_id, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1

    def test_cancel(self) -> None:
        """Test the cancel method of JobSubmissions."""
        response_data = JobSubmissionDetailedViewFactory.build(status=JobSubmissionStatus.CANCELLED)
        job_submission_id = response_data.id

        with respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock:
            route = respx_mock.put(f"/jobbergate/job-submissions/cancel/{job_submission_id}").mock(
                return_value=Response(codes.OK, content=response_data.model_dump_json())
            )

            result = self.job_submissions.cancel(job_submission_id)

        assert route.call_count == 1
        assert result == response_data

    def test_cancel_request_error(self, faker) -> None:
        """Test the cancel method of JobSubmissions with a request error."""
        job_submission_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.put(f"/jobbergate/job-submissions/cancel/{job_submission_id}").mock(
                return_value=Response(codes.INTERNAL_SERVER_ERROR)
            )
            self.job_submissions.cancel(job_submission_id)

        assert route.call_count == 1

    def test_cancel_validation_error(self, faker) -> None:
        """Test the cancel method of JobSubmissions with a validation error."""
        job_submission_id = faker.random_int()

        with (
            respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True) as respx_mock,
            pytest.raises(JobbergateResponseError),
        ):
            route = respx_mock.put(f"/jobbergate/job-submissions/cancel/{job_submission_id}").mock(
                return_value=Response(codes.OK, json={"invalid": "data"})
            )
            self.job_submissions.cancel(job_submission_id)

        assert route.call_count == 1
