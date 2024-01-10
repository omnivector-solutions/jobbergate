from loguru import logger

from jobbergate_agent.clients.slurmrestd import backend_client as slurmrestd_client
from jobbergate_agent.jobbergate.api import fetch_active_submissions, update_status
from jobbergate_agent.jobbergate.constants import JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import SlurmSubmittedJobStatus
from jobbergate_agent.utils.exception import SlurmrestdError
from jobbergate_agent.utils.logging import log_error


async def fetch_job_status(slurm_job_id: int) -> SlurmSubmittedJobStatus:
    logger.debug(f"Fetching slurm job status for slurm job {slurm_job_id}")

    response = await slurmrestd_client.get(f"/job/{slurm_job_id}")

    with SlurmrestdError.handle_errors("Failed to fetch job status from slurm", do_except=log_error):
        response.raise_for_status()
        data = response.json()

    jobs = data["jobs"]
    SlurmrestdError.require_condition(
        len(jobs) == 1,
        f"Couldn't find a slurm job matching id {slurm_job_id}",
    )
    slurm_status = SlurmSubmittedJobStatus.parse_obj(jobs.pop())
    logger.debug(f"Status for slurm job {slurm_job_id} is {slurm_status}")
    return slurm_status


async def finish_active_jobs():
    """
    Mark all active jobs that have completed or failed as finished.
    """
    logger.debug("Started marking completed jobs as finished...")

    logger.debug("Fetching active jobs")
    active_job_submissions = await fetch_active_submissions()

    for active_job_submission in active_job_submissions:
        skip = "skipping to next active job"
        logger.debug(f"Fetching status of job_submission {active_job_submission.id} from slurm")

        try:
            status = await fetch_job_status(active_job_submission.slurm_job_id)
        except Exception:
            logger.debug(f"Fetch status failed...{skip}")
            continue

        if status.jobbergate_status not in {
            JobSubmissionStatus.COMPLETED,
            JobSubmissionStatus.FAILED,
            JobSubmissionStatus.CANCELLED,
        }:
            logger.debug(f"Job is not complete or failed...{skip}")
            continue

        logger.debug(f"Updating job_submission with status={status.jobbergate_status}")

        try:
            await update_status(
                active_job_submission.id,
                status.jobbergate_status,
                report_message=status.state_reason,
            )
        except Exception:
            logger.debug(f"API update failed...{skip}")

    logger.debug("...Finished marking completed jobs as finished")
