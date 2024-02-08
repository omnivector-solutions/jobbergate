import json
from typing import List

from httpx import codes
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.clients.slurmrestd import backend_client as slurmrestd_client

# from jobbergate_agent.jobbergate.api import update_status
from jobbergate_agent.jobbergate.schemas import ActiveJobSubmission, SlurmJobData
from jobbergate_agent.utils.exception import JobbergateApiError, SlurmrestdError
from jobbergate_agent.utils.logging import log_error


async def fetch_job_data(slurm_job_id: int) -> SlurmJobData:
    logger.debug(f"Fetching slurm job status for slurm job {slurm_job_id}")

    response = await slurmrestd_client.get(f"/job/{slurm_job_id}")

    if response.status_code == codes.NOT_FOUND:
        logger.warning(f"Couldn't find a slurm job matching id {slurm_job_id}. Reporting job state as UNKNOWN")
        return SlurmJobData(
            job_id=slurm_job_id,
            job_state="UNKNOWN",
            job_info="{}",
            state_reason=f"Slurm did not find a job matching id {slurm_job_id}",
        )

    with SlurmrestdError.handle_errors("Failed to fetch job state from slurm", do_except=log_error):
        response.raise_for_status()
        data = response.json()
        job_info = data["jobs"][0]
        slurm_state = SlurmJobData.parse_obj(job_info)
        slurm_state.job_info = json.dumps(job_info)
        logger.debug(f"State for slurm job {slurm_job_id} is {slurm_state}")

    return slurm_state


async def fetch_active_submissions() -> List[ActiveJobSubmission]:
    """
    Retrieve a list of active job_submissions.
    """
    with JobbergateApiError.handle_errors("Failed to fetch active job submissions", do_except=log_error):
        response = await jobbergate_api_client.get("jobbergate/job-submissions/agent/active")
        response.raise_for_status()
        active_job_submissions = [ActiveJobSubmission(**ajs) for ajs in response.json().get("items", [])]

    logger.debug(f"Retrieved {len(active_job_submissions)} active job submissions")
    return active_job_submissions


async def update_job_data(
    job_submission_id: int,
    slurm_job_data: SlurmJobData,
) -> None:
    """
    Update a job submission with the job state
    """
    logger.debug(f"Updating {job_submission_id=} with {slurm_job_data=}")

    with JobbergateApiError.handle_errors(
        f"Could not update job data for job submission {job_submission_id} via the API",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.put(
            f"jobbergate/job-submissions/agent/{job_submission_id}",
            json=dict(
                slurm_job_id=slurm_job_data.job_id,
                slurm_job_state=slurm_job_data.job_state,
                slurm_job_info=slurm_job_data.job_info,
                slurm_job_state_reason=slurm_job_data.state_reason,
            ),
        )
        response.raise_for_status()


async def update_active_jobs():
    """
    Update slurm job state for active jobs.
    """
    logger.debug("Started updating slurm job data for active jobs...")

    logger.debug("Fetching active jobs")
    active_job_submissions = await fetch_active_submissions()

    for active_job_submission in active_job_submissions:
        skip = "skipping to next active job"
        logger.debug(f"Fetching slurm job state of job_submission {active_job_submission.id}")

        try:
            slurm_job_data: SlurmJobData = await fetch_job_data(active_job_submission.slurm_job_id)
        except Exception:
            logger.debug(f"Fetch job data failed...{skip}")
            continue

        logger.debug(f"Updating job_submission with slurm job data={slurm_job_data}")

        try:
            await update_job_data(active_job_submission.id, slurm_job_data)
        except Exception:
            logger.debug(f"API update failed...{skip}")

    logger.debug("...Finished updating slurm job data for active jobs")
