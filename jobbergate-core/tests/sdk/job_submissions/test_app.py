from typing import Any
from unittest import mock

import pendulum
import pytest
import respx
from httpx import Response

from jobbergate_core.sdk.job_submissions.app import JobSubmissions
from jobbergate_core.sdk.job_submissions.constants import JobSubmissionStatus
from jobbergate_core.sdk.job_submissions.schemas import JobSubmissionDetailedView
from jobbergate_core.tools.requests import Client, JobbergateResponseError

BASE_URL = "https://testserver"


def client_factory() -> Client:
    """Factory to create a Client instance."""
    return Client(base_url=BASE_URL)


def job_submission_list_view_data_factory() -> dict[str, Any]:
    """Factory to create a list view from job submission data."""
    return {
        "id": 1,
        "name": "template",
        "owner_email": "testing",
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2021-01-01T00:00:00Z",
        "is_archived": False,
        "description": "a template",
        "job_script_id": 10,
        "client_id": "client_1",
        "status": JobSubmissionStatus.CREATED,
    }


def job_submission_detailed_view_data_factory() -> dict[str, Any]:
    """Factory to create a detailed view from job submission data."""
    return job_submission_list_view_data_factory() | {
        "execution_directory": "/tmp",
        "report_message": "success",
        "slurm_job_info": "info",
        "sbatch_arguments": ["--arg1", "--arg2"],
    }


def pack_on_paginated_response(data: dict[str, Any]) -> dict[str, Any]:
    """Pack data into a paginated response."""
    return {
        "items": [data],
        "total": 1,
        "page": 1,
        "size": 1,
        "pages": 1,
    }


class TestJobSubmissions:
    job_submissions = JobSubmissions(client=client_factory())

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create(self, respx_mock) -> None:
        """Test the create method of JobSubmissions."""
        response_data = job_submission_detailed_view_data_factory()
        create_kwargs = {
            "job_script_id": 10,
            "name": "a job",
            "description": "a job description",
            "execution_directory": "/tmp",
            "client_id": "client_1",
        }
        route = respx_mock.post(
            "/jobbergate/job-submissions",
            data=create_kwargs,
        ).mock(return_value=Response(201, json=response_data))

        result = self.job_submissions.create(**create_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

        assert result.job_script_id == response_data["job_script_id"]
        assert result.client_id == response_data["client_id"]
        assert result.status == response_data["status"]

        assert result.execution_directory == response_data["execution_directory"]
        assert result.report_message == response_data["report_message"]
        assert result.slurm_job_info == response_data["slurm_job_info"]
        assert result.sbatch_arguments == response_data["sbatch_arguments"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_request_error(self, respx_mock) -> None:
        """Test the create method of JobSubmissions with a request error."""
        route = respx_mock.post("/jobbergate/job-submissions").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.create(job_script_id=10, name="a job")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_create_validation_error(self, respx_mock) -> None:
        """Test the create method of JobSubmissions with a validation error."""
        route = respx_mock.post("/jobbergate/job-submissions").mock(
            return_value=Response(201, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.create(job_script_id=10, name="a job")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone(self, respx_mock) -> None:
        """Test the clone method of JobSubmissions."""
        response_data = job_submission_detailed_view_data_factory()
        route = respx_mock.post("/jobbergate/job-submissions/clone/1").mock(
            return_value=Response(201, json=response_data)
        )

        result = self.job_submissions.clone(1)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

        assert result.job_script_id == response_data["job_script_id"]
        assert result.client_id == response_data["client_id"]
        assert result.status == response_data["status"]

        assert result.execution_directory == response_data["execution_directory"]
        assert result.report_message == response_data["report_message"]
        assert result.slurm_job_info == response_data["slurm_job_info"]
        assert result.sbatch_arguments == response_data["sbatch_arguments"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_request_error(self, respx_mock) -> None:
        """Test the clone method of JobSubmissions with a request error."""
        route = respx_mock.post("/jobbergate/job-submissions/clone/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.clone(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_clone_validation_error(self, respx_mock) -> None:
        """Test the clone method of JobSubmissions with a validation error."""
        route = respx_mock.post("/jobbergate/job-submissions/clone/1").mock(
            return_value=Response(201, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.clone(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one(self, respx_mock) -> None:
        """Test the get_one method of JobSubmissions."""
        response_data = job_submission_detailed_view_data_factory()
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(200, json=response_data))

        result = self.job_submissions.get_one(1)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

        assert result.job_script_id == response_data["job_script_id"]
        assert result.client_id == response_data["client_id"]
        assert result.status == response_data["status"]

        assert result.execution_directory == response_data["execution_directory"]
        assert result.report_message == response_data["report_message"]
        assert result.slurm_job_info == response_data["slurm_job_info"]
        assert result.sbatch_arguments == response_data["sbatch_arguments"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_request_error(self, respx_mock) -> None:
        """Test the get_one method of JobSubmissions with a request error."""
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_get_one_validation_error(self, respx_mock) -> None:
        """Test the get_one method of JobSubmissions with a validation error."""
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.get_one(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list(self, respx_mock) -> None:
        """Test the list method of JobSubmissions."""
        response_data = pack_on_paginated_response(job_submission_list_view_data_factory())
        list_kwargs = {
            "sort_ascending": True,
            "user_only": True,
            "sort_field": "name",
            "include_archived": True,
            "size": 100,
            "page": 10,
        }
        route = respx_mock.get("/jobbergate/job-submissions", params=list_kwargs).mock(
            return_value=Response(200, json=response_data),
        )

        result = self.job_submissions.get_list(**list_kwargs)

        assert route.call_count == 1
        assert len(result.items) == 1
        assert result.items[0].id == response_data["items"][0]["id"]
        assert result.items[0].job_script_id == response_data["items"][0]["job_script_id"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_request_error(self, respx_mock) -> None:
        """Test the list method of JobSubmissions with a request error."""
        route = respx_mock.get("/jobbergate/job-submissions").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_list_validation_error(self, respx_mock) -> None:
        """Test the list method of JobSubmissions with a validation error."""
        route = respx_mock.get("/jobbergate/job-submissions").mock(return_value=Response(200, json={"invalid": "data"}))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.get_list()

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=False)
    def test_update(self, respx_mock) -> None:
        """Test the update method of JobSubmissions."""
        response_data = job_submission_detailed_view_data_factory()
        update_kwargs: dict[str, Any] = {
            "name": "a new name",
            "description": "a new description",
            "execution_directory": "/tmp",
        }
        route = respx_mock.put(
            "/jobbergate/job-submissions/1",
            data=update_kwargs,
        ).mock(return_value=Response(200, json=response_data))

        result = self.job_submissions.update(1, **update_kwargs)

        assert route.call_count == 1
        assert result.id == response_data["id"]
        assert result.name == response_data["name"]
        assert result.owner_email == response_data["owner_email"]
        assert result.created_at == pendulum.parse(response_data["created_at"])
        assert result.updated_at == pendulum.parse(response_data["updated_at"])
        assert result.is_archived == response_data["is_archived"]
        assert result.description == response_data["description"]

        assert result.job_script_id == response_data["job_script_id"]
        assert result.client_id == response_data["client_id"]
        assert result.status == response_data["status"]

        assert result.execution_directory == response_data["execution_directory"]
        assert result.report_message == response_data["report_message"]
        assert result.slurm_job_info == response_data["slurm_job_info"]
        assert result.sbatch_arguments == response_data["sbatch_arguments"]

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_request_error(self, respx_mock) -> None:
        """Test the update method of JobSubmissions with a request error."""
        route = respx_mock.put("/jobbergate/job-submissions/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.update(1, name="a new name")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_update_validation_error(self, respx_mock) -> None:
        """Test the update method of JobSubmissions with a validation error."""
        route = respx_mock.put("/jobbergate/job-submissions/1").mock(
            return_value=Response(200, json={"invalid": "data"})
        )

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.update(1, name="a new name")

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete(self, respx_mock) -> None:
        """Test the delete method of JobSubmissions."""
        route = respx_mock.delete("/jobbergate/job-submissions/1").mock(return_value=Response(204))

        self.job_submissions.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    def test_delete_request_error(self, respx_mock) -> None:
        """Test the delete method of JobSubmissions with a request error."""
        route = respx_mock.delete("/jobbergate/job-submissions/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.delete(1)

        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id(self, mocked_sleep, respx_mock) -> None:
        """Test the get_one_ensure_slurm_id method of JobSubmissions (happy path)."""
        response_data = job_submission_detailed_view_data_factory()
        response_data["slurm_job_id"] = 12345
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(200, json=response_data))

        result = self.job_submissions.get_one_ensure_slurm_id(1, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1
        assert result.slurm_job_id == response_data["slurm_job_id"]

        assert isinstance(result, JobSubmissionDetailedView)

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_rejected_status(self, mocked_sleep, respx_mock) -> None:
        """Test the get_one_ensure_slurm_id method when the job submission is rejected."""
        response_data = job_submission_detailed_view_data_factory()
        response_data["status"] = JobSubmissionStatus.REJECTED
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(200, json=response_data))

        with pytest.raises(ValueError, match="was rejected and does not have a SLURM job ID"):
            self.job_submissions.get_one_ensure_slurm_id(1, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_timeout(self, mocked_sleep, respx_mock) -> None:
        """Test the get_one_ensure_slurm_id method when SLURM job ID is not set within retries."""
        response_data = job_submission_detailed_view_data_factory()
        response_data["slurm_job_id"] = None
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(200, json=response_data))

        with pytest.raises(TimeoutError, match="was not set within 3 retry attempts"):
            self.job_submissions.get_one_ensure_slurm_id(1, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 2
        assert route.call_count == 3

    @respx.mock(base_url=BASE_URL, assert_all_called=True, assert_all_mocked=True)
    @mock.patch("jobbergate_core.sdk.job_submissions.app.time.sleep")
    def test_get_one_ensure_slurm_id_request_error(self, mocked_sleep, respx_mock) -> None:
        """Test the get_one_ensure_slurm_id method when a request error occurs."""
        route = respx_mock.get("/jobbergate/job-submissions/1").mock(return_value=Response(500))

        with pytest.raises(JobbergateResponseError):
            self.job_submissions.get_one_ensure_slurm_id(1, max_retries=3, waiting_interval=1)

        assert mocked_sleep.call_count == 0
        assert route.call_count == 1
