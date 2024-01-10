import json

import httpx
import pytest
import respx

from jobbergate_agent.jobbergate.constants import JobSubmissionStatus
from jobbergate_agent.jobbergate.finish import fetch_job_status, finish_active_jobs
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import SlurmrestdError


@pytest.mark.parametrize(
    "slurm_status,expected_jobbergate_status",
    (
        ("COMPLETED", JobSubmissionStatus.COMPLETED),
        ("FAILED", JobSubmissionStatus.FAILED),
        ("UNMAPPED_STATUS", JobSubmissionStatus.SUBMITTED),
    ),
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__success(slurm_status, expected_jobbergate_status):
    """
    Test that the ``fetch_job_status()`` function can successfully retrieve
    job_state from Slurm and convert it into a JobSubmissionStatus.
    """
    slurm_id = 123
    slurm_state_reason = "NonZeroExitCode" if slurm_status == "FAILED" else None

    async with respx.mock:
        respx.get(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/{slurm_id}").mock(
            return_value=httpx.Response(
                status_code=200,
                json=dict(
                    jobs=[
                        dict(
                            job_state=slurm_status,
                            job_id=slurm_id,
                            state_reason=slurm_state_reason,
                        ),
                    ],
                ),
            )
        )

        result = await fetch_job_status(slurm_id)

        assert result.job_id == slurm_id
        assert result.job_state == slurm_status
        assert result.state_reason == slurm_state_reason
        assert result.jobbergate_status == expected_jobbergate_status


@pytest.mark.asyncio
async def test_fetch_pending_submissions__raises_SlurmrestdError_if_response_is_not_200():
    """
    Test that the ``fetch_job_status()`` will raise a ``SlurmrestdError`` if the
    response is not a 200.
    """
    async with respx.mock:
        respx.get(f"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/11").mock(return_value=httpx.Response(status_code=400))
        with pytest.raises(SlurmrestdError, match="Failed to fetch job status from slurm"):
            await fetch_job_status(11)


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_finish_active_jobs():
    """
    Test that the ``finish_active_jobs()`` function can fetch active job submissions,
    retrieve the job state from slurm, map it to a ``JobSubmissionStatus``, and update
    the job submission status via the API.
    """
    active_job_submissions_data = {
        "items": [
            dict(id=1, slurm_job_id=11),  # Will complete
            dict(id=2, slurm_job_id=22),  # Jobbergate API gives a 400
            dict(id=3, slurm_job_id=33),  # Slurm REST API gives a 400
            dict(id=4, slurm_job_id=44),  # Slurm has no matching job
            dict(id=5, slurm_job_id=55),  # Job cancelled
            dict(id=6, slurm_job_id=66),  # Unmapped status
        ]
    }

    async with respx.mock:
        fetch_route = respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active")
        fetch_route.mock(
            return_value=httpx.Response(
                status_code=200,
                json=active_job_submissions_data,
            )
        )

        def _map_slurm_request(request: httpx.Request):
            slurm_job_id = int(request.url.path.split("/")[-1])
            mapper = {
                11: "COMPLETED",
                22: "FAILED",
                33: "COMPLETED",
                44: "COMPLETED",
                55: "CANCELLED",
                66: "UNMAPPED_STATUS",
            }
            return httpx.Response(
                status_code=400 if slurm_job_id == 33 else 200,
                json=dict(
                    jobs=[]
                    if slurm_job_id == 44
                    else [
                        dict(job_state=mapper[slurm_job_id]),
                    ],
                ),
            )

        slurm_route = respx.get(url__regex=rf"{SETTINGS.SLURM_RESTD_VERSIONED_URL}/job/\d+")
        slurm_route.mock(side_effect=_map_slurm_request)

        def _map_update_request(request: httpx.Request):
            job_submission_id = int(request.url.path.split("/")[-1])
            return httpx.Response(status_code=400 if job_submission_id == 2 else 200)

        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(side_effect=_map_update_request)

        await finish_active_jobs()

        def _map_slurm_call(request: httpx.Request):
            return int(request.url.path.split("/")[-1])

        assert slurm_route.call_count == 6
        assert [_map_slurm_call(c.request) for c in slurm_route.calls] == [
            11,
            22,
            33,
            44,
            55,
            66,
        ]

        assert fetch_route.call_count == 1

        def _map_update_call(request: httpx.Request):
            return (
                int(request.url.path.split("/")[-1]),
                json.loads(request.content.decode("utf-8"))["status"],
            )

        assert update_route.call_count == 3
        assert [_map_update_call(c.request) for c in update_route.calls] == [
            (1, JobSubmissionStatus.COMPLETED),
            (2, JobSubmissionStatus.FAILED),
            (5, JobSubmissionStatus.CANCELLED),
        ]
