import asyncio
import json
from pathlib import Path
from typing import Any, Dict, cast

from buzz import handle_errors
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client
from jobbergate_agent.clients.slurmrestd import backend_client as slurmrestd_client
from jobbergate_agent.clients.slurmrestd import inject_token
from jobbergate_agent.jobbergate.api import SubmissionNotifier, fetch_pending_submissions, mark_as_submitted
from jobbergate_agent.jobbergate.constants import FileType, JobSubmissionStatus
from jobbergate_agent.jobbergate.schemas import (
    JobScriptFile,
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
    if SETTINGS.SLURM_RESTD_VERSION == "v0.0.39":
        # add required environment variable for slurmrestd v0.0.39
        merged_parameters.setdefault("environment", []).append("FOO=bar")
    return SlurmJobParams.parse_obj(merged_parameters)


async def retrieve_submission_file(file: JobScriptFile) -> str:
    """
    Get a submission file from the backend and return the decoded file content.
    """
    response = await backend_client.get(file.path)
    response.raise_for_status()

    return response.content.decode("utf-8")


async def write_submission_file(file_content: str, filename: str, submit_dir: Path):
    """
    Write a decoded file content to the submit_dir.
    """
    local_script_path = submit_dir / filename
    local_script_path.parent.mkdir(parents=True, exist_ok=True)
    local_script_path.write_bytes(file_content.encode("utf-8"))

    logger.debug(f"Copied file to {local_script_path}")


async def process_supporting_files(pending_job_submission: PendingJobSubmission, submit_dir: Path):
    """
    Process the submission support files.

    Write the support files to the submit_dir if WRITE_SUBMISSION_FILES is set to True.
    Reject the submission if there are support files with WRITE_SUBMISSION_FILES set to False.
    """
    supporting_files = [file for file in pending_job_submission.job_script.files if file.file_type == FileType.SUPPORT]

    if SETTINGS.WRITE_SUBMISSION_FILES:
        # Write the supporting submission support files to the submit dir
        logger.debug(f"Writing supporting submission files to {submit_dir}")

        # Retrieve the files from the backend
        files_to_retrieve = [retrieve_submission_file(file) for file in supporting_files]
        files_content = await asyncio.gather(*files_to_retrieve)

        # Write the files to the submit dir
        files_to_write = [
            write_submission_file(file_content, file.filename, submit_dir)
            for file_content, file in zip(files_content, supporting_files)
        ]
        await asyncio.gather(*files_to_write)
    else:
        # Reject the submission if there are supporting files with WRITE_SUBMISSION_FILES set to False
        logger.debug(f"Can't write files for submission {pending_job_submission.id}")

        JobSubmissionError.require_condition(
            not supporting_files,
            "Job submission rejected. The submission has supporting files that can't be downloaded to "
            "the execution dir. Set `WRITE_SUBMISSION_FILES` setting to `True` to download the "
            "job script files to the execution dir.",
        )


async def get_job_script_file(pending_job_submission: PendingJobSubmission, submit_dir: Path) -> str:
    """
    Get the job script file from the backend.

    Write the job script file to the submit_dir if WRITE_SUBMISSION_FILES is set to True.
    """
    job_script_file = None

    for file in pending_job_submission.job_script.files:
        if file.file_type == FileType.ENTRYPOINT:  # Should have only one entrypoint
            job_script_file = file
            break

    JobSubmissionError.require_condition(
        job_script_file,
        "Could not find an executable script in retrieved job script data.",
    )

    # Make static type checkers happy
    assert job_script_file is not None

    job_script = await retrieve_submission_file(job_script_file)

    if SETTINGS.WRITE_SUBMISSION_FILES:
        await write_submission_file(job_script, job_script_file.filename, submit_dir)

    return job_script


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
        "Username could not be resolved",
        raise_exc_class=JobSubmissionError,
        do_except=notify_submission_rejected.report_error,
    ):
        email = pending_job_submission.owner_email
        name = pending_job_submission.name
        mapper_class_name = user_mapper.__class__.__name__
        logger.debug(f"Fetching username for email {email} with mapper {mapper_class_name}")
        username = user_mapper[email]
        logger.debug(f"Using local slurm user {username} for job submission")

    async with handle_errors_async(
        "Error processing job-script files",
        raise_exc_class=JobSubmissionError,
        do_except=notify_submission_rejected.report_error,
    ):
        submit_dir = pending_job_submission.execution_directory or SETTINGS.DEFAULT_SLURM_WORK_DIR

        logger.debug(f"Processing submission files for job submission {pending_job_submission.id}")
        await process_supporting_files(pending_job_submission, submit_dir)

        logger.debug(f"Fetching job script for job submission {pending_job_submission.id}")
        job_script = await get_job_script_file(pending_job_submission, submit_dir)

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

    response = await slurmrestd_client.post(
        "/job/submit",
        auth=lambda r: inject_token(r, username=username),
        json=json.loads(payload.json()),
    )

    async with handle_errors_async(
        "Failed to submit job to slurm",
        raise_exc_class=SlurmrestdError,
        do_except=notify_submission_rejected.report_error,
    ):
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
