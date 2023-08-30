from __future__ import annotations

from dataclasses import dataclass

from buzz import DoExceptParams
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.jobbergate.constants import JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, PendingJobSubmission
from jobbergate_agent.utils.exception import JobbergateApiError
from jobbergate_agent.utils.logging import log_error


async def fetch_pending_submissions() -> list[PendingJobSubmission]:
    """
    Retrieve a list of pending job_submissions.
    """
    with JobbergateApiError.handle_errors(
        "Failed to fetch pending job submissions",
        do_except=log_error,
    ):
        response = await backend_client.get("/jobbergate/job-submissions/agent/pending")
        response.raise_for_status()
        pending_job_submissions = [PendingJobSubmission(**pjs) for pjs in response.json().get("items", [])]

    logger.debug(f"Retrieved {len(pending_job_submissions)} pending job submissions")
    return pending_job_submissions


async def fetch_active_submissions() -> list[ActiveJobSubmission]:
    """
    Retrieve a list of active job_submissions.
    """
    with JobbergateApiError.handle_errors(
        "Failed to fetch active job submissions",
        do_except=log_error,
    ):
        response = await backend_client.get("jobbergate/job-submissions/agent/active")
        response.raise_for_status()
        active_job_submissions = [ActiveJobSubmission(**ajs) for ajs in response.json().get("items", [])]

    logger.debug(f"Retrieved {len(active_job_submissions)} active job submissions")
    return active_job_submissions


async def mark_as_submitted(job_submission_id: int, slurm_job_id: int):
    """
    Mark job_submission as submitted in the Jobbergate API.
    """
    logger.debug(f"Marking job {job_submission_id=} as {JobSubmissionStatus.SUBMITTED} ({slurm_job_id=})")

    with JobbergateApiError.handle_errors(
        f"Could not mark job submission {job_submission_id} as submitted via the API",
        do_except=log_error,
    ):
        response = await backend_client.put(
            f"jobbergate/job-submissions/agent/{job_submission_id}",
            json=dict(
                status=JobSubmissionStatus.SUBMITTED,
                slurm_job_id=slurm_job_id,
            ),
        )
        response.raise_for_status()


@dataclass
class SubmissionNotifier:
    """
    Class used to update the status for a job submission when some error is detected.

    It is designed to work together with py-buzz, extracting the error message,
    logging it and sending it to Jobbergate API.
    """

    job_submission_id: int
    status: JobSubmissionStatus

    async def report_error(self, params: DoExceptParams) -> None:
        """
        Update the status for a job submission.

        :param DoExceptParams params: Dataclass for the ``do_except`` user supplied handling method.
        """
        log_error(params)
        logger.debug(f"Informing Jobbergate that the job submission was {self.status}")
        await update_status(self.job_submission_id, self.status, report_message=params.final_message)


async def update_status(
    job_submission_id: int,
    status: JobSubmissionStatus,
    *,
    report_message: str | None = None,
) -> None:
    """
    Update a job submission with a status
    """
    logger.debug(f"Updating {job_submission_id=} with {status=} due to {report_message=}")

    with JobbergateApiError.handle_errors(
        f"Could not update status for job submission {job_submission_id} via the API",
        do_except=log_error,
    ):
        payload = {"status": status}
        if report_message:
            payload["report_message"] = report_message
        response = await backend_client.put(f"jobbergate/job-submissions/agent/{job_submission_id}", json=payload)
        response.raise_for_status()
