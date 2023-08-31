import json
from typing import Any, Dict, cast

from buzz import handle_errors
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.clients.slurmrestd import backend_client as slurmrestd_client
from jobbergate_agent.clients.slurmrestd import inject_token
from jobbergate_agent.jobbergate.api import SubmissionNotifier, fetch_pending_submissions, mark_as_submitted
from jobbergate_agent.jobbergate.constants import FileType, JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import (
    PendingJobSubmission,
    SlurmJobParams,
    SlurmJobSubmission,
    SlurmSubmitResponse,
)
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import (
    JobSubmissionError,
    SlurmParameterParserError,
    SlurmrestdError,
    handle_errors_async,
)
from jobbergate_agent.utils.logging import log_error
from jobbergate_agent.utils.user_mapper import SlurmUserMapper, manufacture


def unpack_error_from_slurm_response(response: SlurmSubmitResponse) -> str:
    """
    Unpack the error message from the response of a slurmrestd request.
    """
    return "; ".join(e.error for e in response.errors if e.error)


def get_job_parameters(slurm_parameters: Dict[str, Any], **kwargs) -> SlurmJobParams:
    """
    Obtain the job parameters from the slurm_parameters dict and additional values.

    Extra keyword arguments can be used to supply default values for any parameter
    (like name or current_working_directory). Note they may be overwritten by
    values from slurm_parameters.
    """
    merged_parameters = {**kwargs, **slurm_parameters}
    return SlurmJobParams.parse_obj(merged_parameters)


async def submit_job_script(
    pending_job_submission: PendingJobSubmission,
    user_mapper: SlurmUserMapper,
) -> int:
    """
    Submit a Job Script to slurm via the Slurm REST API.

    :param: pending_job_submission: A job_submission with fields needed to submit.
    :returns: The ``slurm_job_id`` for the submitted job
    """

    notify_submission_rejected = SubmissionNotifier(pending_job_submission.id, JobSubmissionStatus.REJECTED)

    async with handle_errors_async(
        "An internal error occurred while processing the job-submission",
        raise_exc_class=JobSubmissionError,
        do_except=notify_submission_rejected.report_error,
    ):
        email = pending_job_submission.owner_email
        name = pending_job_submission.name
        mapper_class_name = user_mapper.__class__.__name__
        logger.debug(f"Fetching username for email {email} with mapper {mapper_class_name}")
        username = user_mapper[email]
        logger.debug(f"Using local slurm user {username} for job submission")

        submit_dir = pending_job_submission.execution_directory or SETTINGS.DEFAULT_SLURM_WORK_DIR

        job_script = None

        for metadata in pending_job_submission.job_script.files:
            local_script_path = submit_dir / metadata.filename
            local_script_path.parent.mkdir(parents=True, exist_ok=True)

            response = await backend_client.get(metadata.path)
            response.raise_for_status()
            local_script_path.write_bytes(response.content)

            if metadata.file_type == FileType.ENTRYPOINT:
                job_script = response.content.decode("utf-8")

            logger.debug(f"Copied job script file to {local_script_path}")

        JobSubmissionError.require_condition(
            job_script,
            "Could not find an executable script in retrieved job script data.",
        )

    async with handle_errors_async(
        "Failed to extract Slurm parameters",
        raise_exc_class=SlurmParameterParserError,
        do_except=notify_submission_rejected.report_error,
    ):
        job_parameters = get_job_parameters(
            pending_job_submission.execution_parameters,
            name=name,
            current_working_directory=submit_dir,
            standard_output=submit_dir / f"{name}.out",
            standard_error=submit_dir / f"{name}.err",
        )

    payload = SlurmJobSubmission(script=job_script, job=job_parameters)
    logger.debug(f"Submitting pending job submission {pending_job_submission.id} " f"to slurm with payload {payload}")

    async with handle_errors_async(
        "Failed to submit job to slurm",
        raise_exc_class=SlurmrestdError,
        do_except=notify_submission_rejected.report_error,
    ):
        response = await slurmrestd_client.post(
            "/job/submit",
            auth=lambda r: inject_token(r, username=username),
            json=json.loads(payload.json()),
        )
        logger.debug(f"Slurmrestd response: {response.text}")
        sub_data = SlurmSubmitResponse.parse_raw(response.content)
        with handle_errors(unpack_error_from_slurm_response(sub_data)):
            response.raise_for_status()

    # Make static type checkers happy.
    slurm_job_id = cast(int, sub_data.job_id)

    logger.debug(f"Received slurm job id {slurm_job_id} for job submission {pending_job_submission.id}")

    return slurm_job_id


async def submit_pending_jobs():
    """
    Submit all pending jobs and update them with ``SUBMITTED`` status and slurm_job_id.

    :returns: The ``slurm_job_id`` for the submitted job
    """
    logger.debug("Started submitting pending jobs...")

    logger.debug("Building user-mapper")
    user_mapper = manufacture()

    logger.debug("Fetching pending jobs...")
    pending_job_submissions = await fetch_pending_submissions()

    for pending_job_submission in pending_job_submissions:
        logger.debug(f"Submitting pending job_submission {pending_job_submission.id}")
        with JobSubmissionError.handle_errors(
            (f"Failed to submit pending job_submission {pending_job_submission.id}" "...skipping to next pending job"),
            do_except=log_error,
            do_else=lambda: logger.debug(f"Finished submitting pending job_submission {pending_job_submission.id}"),
            re_raise=False,
        ):
            slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)

            await mark_as_submitted(pending_job_submission.id, slurm_job_id)

    logger.debug("...Finished submitting pending jobs")
