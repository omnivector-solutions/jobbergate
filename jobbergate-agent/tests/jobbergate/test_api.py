"""
Define tests for the Jobbergate API interface functions.
"""

import json

import httpx
import pytest
import respx
from buzz import DoExceptParams

from jobbergate_agent.jobbergate.api import (
    SubmissionNotifier,
    fetch_active_submissions,
    fetch_pending_submissions,
    mark_as_submitted,
    update_status,
)
from jobbergate_agent.jobbergate.constants import JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, PendingJobSubmission
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, JobSubmissionError


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__success(dummy_job_script_files):
    """
    Test that the ``fetch_pending_submissions()`` function can successfully retrieve
    PendingJobSubmission objects from the API.
    """
    pending_job_submissions_data = {
        "items": [
            dict(
                id=1,
                name="sub1",
                owner_email="email1@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=111,
            ),
            dict(
                id=2,
                name="sub2",
                owner_email="email2@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=222,
            ),
            dict(
                id=3,
                name="sub3",
                owner_email="email3@dummy.com",
                job_script={"files": dummy_job_script_files},
                slurm_job_id=333,
            ),
        ]
    }
    async with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        pending_job_submissions = await fetch_pending_submissions()
        for i, pending_job_submission in enumerate(pending_job_submissions):
            assert isinstance(pending_job_submission, PendingJobSubmission)
            assert i + 1 == pending_job_submission.id


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__raises_JobbergateApiError_if_response_is_not_200():  # noqa
    """
    Test that the ``fetch_pending_submissions()`` function will raise a
    JobbergateApiError if the response from the API is not OK (200).
    """
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(status_code=400)
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch pending"):
            await fetch_pending_submissions()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_fetch_pending_submissions__raises_JobbergateApiError_if_response_cannot_be_deserialized():  # noqa
    """
    Test that the ``fetch_pending_submissions()`` function will raise a
    JobbergateApiError if it fails to convert the response to a PendingJobSubmission.
    """
    pending_job_submissions_data = [
        dict(bad="data"),
    ]
    with respx.mock:
        respx.get(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/pending").mock(
            return_value=httpx.Response(
                status_code=200,
                json=pending_job_submissions_data,
            )
        )

        with pytest.raises(JobbergateApiError, match="Failed to fetch pending"):
            await fetch_pending_submissions()


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
async def test_mark_as_submitted__success():
    """
    Test that the ``mark_as_submitted()`` can successfully update a job submission
    with its ``slurm_job_id`` and a status of ``SUBMITTED``.
    """
    with respx.mock:
        update_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/1")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await mark_as_submitted(1, 111)
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_mark_as_submitted__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``mark_as_submitted()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/1")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError,
            match="Could not mark job submission 1 as submitted",
        ):
            await mark_as_submitted(1, 111)
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_status__success():
    """
    Test that the ``update_status()`` can successfully update a job submission
    with a ``JobSubmissionStatus``.
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await update_status(1, JobSubmissionStatus.COMPLETED)
        assert update_route.calls.last.request.content == json.dumps(dict(status=JobSubmissionStatus.COMPLETED)).encode(
            "utf-8"
        )

        await update_status(2, JobSubmissionStatus.FAILED, report_message="It failed")
        assert update_route.calls.last.request.content == json.dumps(
            dict(status=JobSubmissionStatus.FAILED, report_message="It failed")
        ).encode("utf-8")

        assert update_route.call_count == 2


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_update_status__raises_JobbergateApiError_if_the_response_is_not_200():
    """
    Test that the ``update_status()`` function will raise a JobbergateApiError if
    the response from the API is not OK (200).
    """
    with respx.mock:
        update_route = respx.put(url__regex=rf"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/\d+")
        update_route.mock(return_value=httpx.Response(status_code=400))

        with pytest.raises(
            JobbergateApiError,
            match="Could not update status for job submission 1",
        ):
            await update_status(1, JobSubmissionStatus.CREATED)
        assert update_route.called


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_access_token")
async def test_notify_submission_rejected():
    """
    Test that ``notify_submission_rejected`` can send a message to Jobbergate
    and set the job status to REJECTED.
    """
    job_submission_id = 1
    report_message = f"An expected failure occurred when submit {job_submission_id=} at 'unittest'"

    params = DoExceptParams(
        JobSubmissionError,
        final_message=report_message,
        trace=None,
    )

    notify_submission_rejected = SubmissionNotifier(job_submission_id, JobSubmissionStatus.REJECTED)

    async with respx.mock:
        update_route = respx.put(f"{SETTINGS.BASE_API_URL}/jobbergate/job-submissions/agent/{job_submission_id}")
        update_route.mock(return_value=httpx.Response(status_code=200))

        await notify_submission_rejected.report_error(params)

        assert update_route.call_count == 1
        assert update_route.calls.last.request.content == json.dumps(
            dict(
                status=JobSubmissionStatus.REJECTED,
                report_message=report_message,
            ),
        ).encode("utf-8")
