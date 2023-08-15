"""
Define tests for the submission functions of the jobbergate section.
"""

import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from jobbergate_agent.jobbergate.constants import JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import (
    PendingJobSubmission,
    SlurmJobParams,
    SlurmJobSubmission,
    SlurmSubmitResponse,
)
from jobbergate_agent.jobbergate.submit import (
    get_job_parameters,
    submit_job_script,
    submit_pending_jobs,
    unpack_error_from_slurm_response,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobSubmissionError, SlurmrestdError
from jobbergate_agent.utils.user_mapper import SingleUserMapper


@pytest.mark.asyncio
async def test_submit_job_script__success(dummy_pending_job_submission_data, dummy_template_source):
    """
    Test that the ``submit_job_script()`` successfully submits a job.

    Verifies that a PendingJobSubmission instance is submitted via the Slurm REST API
    and that a ``slurm_job_id`` is returned. Verifies that LDAP was used to retrieve
    the username.
    """
    user_mapper = SingleUserMapper("dummy-user")

    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    name = pending_job_submission.name

    async with respx.mock:
        submit_route = respx.post(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/submit")
        submit_route.mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(job_id=13),
            )
        )

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

        assert slurm_job_id == 13
        assert submit_route.call_count == 1
        assert download_route.call_count == 1
        last_request = submit_route.calls.last.request
        assert last_request.method == "POST"
        assert last_request.headers["x-slurm-user-name"] == "dummy-user"
        assert last_request.headers["x-slurm-user-token"] == "default-dummy-token"
        actual_response = last_request.content.decode("utf-8")
        expected_response = SlurmJobSubmission(
            script=dummy_template_source,
            job=SlurmJobParams(
                name=name,
                current_working_directory=SETTINGS.DEFAULT_SLURM_WORK_DIR,
                standard_output=SETTINGS.DEFAULT_SLURM_WORK_DIR / f"{name}.out",
                standard_error=SETTINGS.DEFAULT_SLURM_WORK_DIR / f"{name}.err",
            ),
        ).json()

        assert actual_response == expected_response


@pytest.mark.asyncio
async def test_submit_job_script__with_non_default_execution_directory(
    dummy_pending_job_submission_data,
    dummy_template_source,
    mocker,
    tmp_path,
):
    """
    Test that the ``submit_job_script()`` successfully submits a job with an exec dir.

    Verifies that a PendingJobSubmission instance is submitted via the Slurm REST API
    and that a ``slurm_job_id`` is returned. Verifies that the execution_directory is
    taken from the request and submitted to slurm rest api.
    """
    user_mapper = SingleUserMapper("dummy-user")

    mocker.patch("jobbergate_agent.identity.slurmrestd.acquire_token", return_value="dummy-token")
    exe_path = tmp_path / "exec"
    exe_path.mkdir()
    pending_job_submission = PendingJobSubmission(
        **dummy_pending_job_submission_data,
        execution_directory=exe_path,
    )
    name = pending_job_submission.name

    job_parameters = get_job_parameters(
        pending_job_submission.execution_parameters,
        name=name,
        current_working_directory=exe_path,
        standard_output=exe_path / f"{name}.out",
        standard_error=exe_path / f"{name}.err",
    )

    async with respx.mock:
        submit_route = respx.post(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/submit")
        submit_route.mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(job_id=13),
            )
        )

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

        assert slurm_job_id == 13
        assert submit_route.call_count == 1
        assert download_route.call_count == 1
        last_request = submit_route.calls.last.request
        assert last_request.method == "POST"
        assert last_request.headers["x-slurm-user-name"] == "dummy-user"
        assert last_request.headers["x-slurm-user-token"] == "dummy-token"
        assert (
            last_request.content.decode("utf-8")
            == SlurmJobSubmission(
                script=dummy_template_source,
                job=job_parameters,
            ).json()
        )


@pytest.mark.asyncio
async def test_submit_job_script__raises_exception_if_no_executable_script_was_found(
    dummy_pending_job_submission_data, mocker
):
    """
    Test that the ``submit_job_script()`` will raise a JobSubmissionError if it cannot
    find an executable job script in the retrieved pending job submission data
    and that the job submission status is updated to rejected.
    """
    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)
    pending_job_submission.job_script.files = []

    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/oauth/token").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(access_token="dummy-token"),
            )
        )
        update_route = respx.put(
            f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/{pending_job_submission.id}"
        )
        update_route.mock(return_value=httpx.Response(status_code=200))

        with pytest.raises(JobSubmissionError, match="Could not find an executable"):
            await submit_job_script(pending_job_submission, SingleUserMapper())

    assert update_route.call_count == 1


@pytest.mark.asyncio
async def test_submit_job_script__raises_exception_if_submit_call_response_is_not_200(
    dummy_pending_job_submission_data, mocker, dummy_template_source
):
    """
    Test that ``submit_job_script()`` raises an exception if the response from Slurm
    REST API is nota 200. Verifies that the error message is included in the raised
    exception and that the job submission status is updated to rejected.
    """
    user_mapper = SingleUserMapper("dummy-user")

    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)

    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/oauth/token").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(access_token="dummy-token"),
            )
        )
        update_route = respx.put(
            f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/{pending_job_submission.id}"
        )
        update_route.mock(return_value=httpx.Response(status_code=200))

        submit_route = respx.post(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/submit")
        submit_route.mock(
            return_value=httpx.Response(
                status_code=400,
                json=dict(
                    errors=[
                        dict(
                            error="BOOM!",
                            errno=13,
                        ),
                    ],
                ),
            )
        )

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        with pytest.raises(
            SlurmrestdError,
            match="Failed to submit job to slurm",
        ):
            await submit_job_script(pending_job_submission, user_mapper)

    assert update_route.call_count == 1
    assert download_route.call_count == 1


@pytest.mark.asyncio
async def test_submit_job_script__raises_exception_if_response_cannot_be_unpacked(
    dummy_pending_job_submission_data,
    mocker,
    dummy_template_source,
):
    """
    Test that ``submit_job_script()`` raises an exception if the response from Slurm
    REST API is nota 200. Verifies that the error message is included in the raised
    exception and that the job submission status is updated to rejected.
    """
    user_mapper = SingleUserMapper("dummy-user")

    pending_job_submission = PendingJobSubmission(**dummy_pending_job_submission_data)

    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/oauth/token").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(access_token="dummy-token"),
            )
        )
        update_route = respx.put(
            f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/{pending_job_submission.id}"
        )
        update_route.mock(return_value=httpx.Response(status_code=200))

        submit_route = respx.post(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/submit")
        submit_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content="BAD DATA",
            )
        )

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        with pytest.raises(SlurmrestdError, match="Failed to submit job to slurm"):
            await submit_job_script(pending_job_submission, user_mapper)

    assert update_route.call_count == 1
    assert download_route.call_count == 1


@pytest.mark.asyncio
async def test_submit_pending_jobs(
    dummy_job_script_files,
    tweak_settings,
    dummy_template_source,
):
    """
    Test that the ``submit_pending_jobs()`` function can fetch pending job submissions,
    submit each to slurm via the Slurm REST API, and update the job submission via the
    Jobbergate API.
    """
    pending_job_submissions_data = {
        "items": [
            dict(
                id=1,
                name="sub1",
                owner_email="email1@dummy.com",
                job_script={"files": dummy_job_script_files},
            ),
            dict(
                id=2,
                name="sub2",
                owner_email="email2@dummy.com",
                job_script={"files": dummy_job_script_files},
            ),
            dict(
                id=3,
                name="sub3",
                owner_email="email3@dummy.com",
                job_script={"files": dummy_job_script_files},
            ),
        ]
    }
    async with respx.mock:
        respx.post(f"https://{SETTINGS.OIDC_DOMAIN}/protocol/openid-connect/token").mock(
            return_value=httpx.Response(status_code=200, json=dict(access_token="dummy-token"))
        )
        fetch_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending")
        fetch_route.mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )
        update_1_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/1")
        update_1_route.mock(return_value=httpx.Response(status_code=200))

        update_2_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/2")
        update_2_route.mock(return_value=httpx.Response(status_code=400))

        update_3_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/3")
        update_3_route.mock(return_value=httpx.Response(status_code=200))

        download_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-scripts/1/upload/application.sh")
        download_route.mock(
            return_value=httpx.Response(
                status_code=200,
                content=dummy_template_source.encode("utf-8"),
            ),
        )

        def _submit_side_effect(request):
            req_data = request.content.decode("utf-8")
            name = json.loads(req_data)["job"]["name"]
            fake_slurm_job_id = int(name.replace("sub", "")) * 11
            if name == "sub3":
                return httpx.Response(
                    status_code=400,
                    json=dict(errors=dict(error="BOOM!")),
                )
            else:
                return httpx.Response(
                    status_code=200,
                    json=dict(job_id=fake_slurm_job_id),
                )

        submit_route = respx.post(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/submit")
        submit_route.mock(side_effect=_submit_side_effect)

        with tweak_settings(SINGLE_USER_SUBMITTER="dummy-user"):
            await submit_pending_jobs()

        assert update_1_route.call_count == 1
        assert update_1_route.calls.last.request.content == json.dumps(
            dict(
                status=JobSubmissionStatus.SUBMITTED,
                slurm_job_id=11,
            )
        ).encode("utf-8")

        assert update_2_route.call_count == 1
        assert update_2_route.calls.last.request.content == json.dumps(
            dict(
                status=JobSubmissionStatus.SUBMITTED,
                slurm_job_id=22,
            )
        ).encode("utf-8")

        assert update_3_route.call_count == 1  # called to notify the job was rejected
        assert download_route.call_count == len(pending_job_submissions_data["items"])


class TestGetJobParameters:
    """
    Test the ``get_job_parameters()`` function.
    """

    def test_base_case__fail(self):
        """
        Base case should fail, since name is a required field.
        """
        with pytest.raises(
            ValidationError,
            match="1 validation error for SlurmJobParams\nname\n  field required.*",
        ):
            get_job_parameters(slurm_parameters={})

    def test_base_case__success(self):
        """
        Base case should succeed with a valid name.
        """
        desired_value = SlurmJobParams(name="test-test")

        actual_value = get_job_parameters(slurm_parameters={}, name="test-test")

        assert actual_value == desired_value

    def test_priority(self):
        """
        Test that slurm parameters have priority over extra keyword arguments.
        """
        desired_value = SlurmJobParams(name="high-priority")

        actual_value = get_job_parameters(slurm_parameters=dict(name="high-priority"), name="test-test")

        assert actual_value == desired_value

    def test_extra_arguments(self):
        """
        Test that SlurmJobParams can be constructed with extra keyword arguments.
        """
        desired_value = SlurmJobParams(foo="bar", name="test-test")

        actual_value = get_job_parameters(slurm_parameters=dict(foo="bar"), name="test-test")

        assert actual_value == desired_value


def test_unpack_error_from_slurm_response():
    """
    Test that the function ``unpack_error_from_slurm_response()`` returns the correct error.
    """
    response = httpx.Response(
        status_code=400,
        json={
            "meta": {
                "plugin": {"type": "openapi/v0.0.36", "name": "REST v0.0.36"},
                "Slurm": {
                    "version": {"major": 21, "micro": 6, "minor": 8},
                    "release": "21.08.6",
                },
            },
            "errors": [
                {"error": "Unable to read integer value", "error_code": 9202},
                {
                    "error": "process failed for key wait_all_nodes with error: Unspecified error",
                    "error_code": 1,
                },
                {"error_code": 9001, "error": "Failure during parsing"},
            ],
        },
    )

    desired_message = (
        "Unable to read integer value;"
        " process failed for key wait_all_nodes with error: Unspecified error;"
        " Failure during parsing"
    )
    actual_error = unpack_error_from_slurm_response(SlurmSubmitResponse.parse_raw(response.content))

    assert actual_error == desired_message
