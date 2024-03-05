import json
from unittest import mock

import httpx
import pytest
import respx

from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, SlurmJobData
from jobbergate_agent.jobbergate.update import (
    fetch_active_submissions,
    fetch_job_data,
    update_active_jobs,
    update_job_data,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_job_data__success():
    """
    Test that the ``fetch_job_data()`` function can successfully retrieve
    job data from Slurm as a ``SlurmJobData``.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.return_value = json.dumps(
        dict(
            job_state="FAILED",
            job_id=123,
            state_reason="NonZeroExitCode",
            foo="bar",
        )
    )

    result: SlurmJobData = await fetch_job_data(123, mocked_sbatch)

    assert result.job_id == 123
    assert result.job_state == "FAILED"
    assert result.state_reason == "NonZeroExitCode"
    assert result.job_info is not None
    assert json.loads(result.job_info) == dict(
        job_state="FAILED",
        job_id=123,
        state_reason="NonZeroExitCode",
        foo="bar",
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_job_data__reports_status_as_UNKOWN_if_slurm_job_id_is_not_found():
    """
    Test that the ``fetch_job_data()`` reports the job state as UNKNOWN if the job matching job id is not found.
    """
    mocked_sbatch = mock.MagicMock()
    mocked_sbatch.get_job_info.side_effect = RuntimeError("Job not found")

    result: SlurmJobData = await fetch_job_data(123, mocked_sbatch)

    assert result.job_id == 123
    assert result.job_info == "{}"
    assert result.job_state == "UNKNOWN"
    assert result.state_reason == "Slurm did not find a job matching id 123"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__success():
    """
    Test that the ``fetch_active_submissions()`` function can successfully retrieve
    ActiveJobSubmission objects from the API.
    """
    pending_job_submissions_data = {
        "items": [
            dict(
                id=1,
                slurm_job_id=11,
            ),
            dict(
                id=2,
                slurm_job_id=22,
            ),
            dict(
                id=3,
                slurm_job_id=33,
            ),
        ]
    }
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        active_job_submissions = fetch_active_submissions()
        for i, active_job_submission in enumerate(await active_job_submissions):
            assert isinstance(active_job_submission, ActiveJobSubmission)
            assert i + 1 == active_job_submission.id
            assert (i + 1) * 11 == active_job_submission.slurm_job_id


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__raises_JobbergateApiError_if_response_is_not_200():  # noqa
    """
    Test that the ``fetch_active_submissions()`` function will raise a
    JobbergateApiError if the response from the API is not OK (200).
    """
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(status_code=400)
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch"):
            await fetch_active_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_active_submissions__raises_JobbergateApiError_if_response_cannot_be_deserialized():  # noqa
    """
    Test that the ``fetch_active_submissions()`` function will raise a
    JobbergateApiError if it fails to convert the response to an ActiveJobSubmission.
    """
    active_job_submissions_data = [
        dict(bad="data"),
    ]
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/active").mock(
            return_value=httpx.Response(
                status_code=200,
                json=active_job_submissions_data,
            )
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch active"):
            await fetch_active_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_job_data__success():
    """
    Test that the ``update_job_data()`` can successfully update a job submission with a ``SlurmJobData``.
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await update_job_data(
            1,
            SlurmJobData(
                job_id=13,
                job_state="FAILED",
                job_info="some job info",
                state_reason="Something happened",
            ),
        )

        assert update_route.calls.last.request.content == json.dumps(
            dict(
                slurm_job_id=13,
                slurm_job_state="FAILED",
                slurm_job_info="some job info",
                slurm_job_state_reason="Something happened",
            )
        ).encode("utf-8")


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_job_data__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``update_status()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(JobbergateApiError, match="Could not update job data for job submission 1"):
            await update_job_data(
                1,
                SlurmJobData(
                    job_id=13,
                    job_state="FAILED",
                    job_info="some job info",
                    state_reason="Something happened",
                ),
            )
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_active_jobs(mocker):
    """
    Test that the ``update_active_jobs()`` function can fetch active job submissions,
    retrieve the job data from slurm, and update the slurm job data on the submission via the API.
    """

    mocked_sbatch = mock.MagicMock()
    mocker.patch("jobbergate_agent.jobbergate.update.SbatchHandler", return_value=mocked_sbatch)

    mocker.patch(
        "jobbergate_agent.jobbergate.update.fetch_active_submissions",
        return_value=[
            ActiveJobSubmission(id=1, slurm_job_id=11),  # Will update
            ActiveJobSubmission(id=2, slurm_job_id=22),  # fetch_job_data throws exception
            ActiveJobSubmission(id=3, slurm_job_id=33),  # update_job_data throws exception
        ],
    )

    def _mocked_fetch_job_data(slurm_job_id, *args, **kwargs):
        if slurm_job_id == 22:
            raise Exception("BOOM!")
        return {
            11: SlurmJobData(
                job_id=11,
                job_state="FAILED",
                job_info="some job info",
                state_reason="Something happened",
            ),
            33: SlurmJobData(
                job_id=33,
                job_state="COMPLETED",
                job_info="some more job info",
                state_reason="It finished",
            ),
        }[slurm_job_id]

    def _mocked_update_job_data(job_submission_id, slurm_job_data):
        if job_submission_id == 3:
            raise Exception("BANG!")

    mock_fetch = mocker.patch("jobbergate_agent.jobbergate.update.fetch_job_data", side_effect=_mocked_fetch_job_data)
    mock_update = mocker.patch(
        "jobbergate_agent.jobbergate.update.update_job_data", side_effect=_mocked_update_job_data
    )

    await update_active_jobs()

    mock_fetch.assert_has_calls(
        [mocker.call(11, mocked_sbatch), mocker.call(22, mocked_sbatch), mocker.call(33, mocked_sbatch)]
    )
    assert mock_fetch.call_count == 3

    mock_update.assert_has_calls(
        [
            mocker.call(
                1,
                SlurmJobData(
                    job_id=11,
                    job_state="FAILED",
                    job_info="some job info",
                    state_reason="Something happened",
                ),
            ),
            mocker.call(
                3,
                SlurmJobData(
                    job_id=33,
                    job_state="COMPLETED",
                    job_info="some more job info",
                    state_reason="It finished",
                ),
            ),
        ]
    )
    assert mock_update.call_count == 2
