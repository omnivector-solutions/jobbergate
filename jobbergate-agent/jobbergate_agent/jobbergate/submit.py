from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

from buzz import DoExceptParams
from jobbergate_core.tools.sbatch import SbatchHandler
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.jobbergate.constants import FileType
from jobbergate_agent.jobbergate.schemas import JobScriptFile, PendingJobSubmission
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, JobSubmissionError, handle_errors_async
from jobbergate_agent.utils.logging import log_error
from jobbergate_agent.utils.user_mapper import SlurmUserMapper, manufacture


async def retrieve_submission_file(file: JobScriptFile) -> str:
    """
    Get a submission file from the backend and return the decoded file content.
    """
    response = await jobbergate_api_client.get(file.path)
    response.raise_for_status()

    return response.content.decode("utf-8")


async def write_submission_file(file_content: str, filename: str, submit_dir: Path) -> Path:
    """
    Write a decoded file content to the submit_dir.
    """
    local_script_path = submit_dir / filename
    local_script_path.parent.mkdir(parents=True, exist_ok=True)
    local_script_path.write_bytes(file_content.encode("utf-8"))

    logger.debug(f"Copied file to {local_script_path}")
    return local_script_path


async def process_supporting_files(pending_job_submission: PendingJobSubmission, submit_dir: Path) -> list[Path]:
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
        return await asyncio.gather(*files_to_write)
    else:
        # Reject the submission if there are supporting files with WRITE_SUBMISSION_FILES set to False
        logger.debug(f"Can't write files for submission {pending_job_submission.id}")

        JobSubmissionError.require_condition(
            not supporting_files,
            "Job submission rejected. The submission has supporting files that can't be downloaded to "
            "the execution dir. Set `WRITE_SUBMISSION_FILES` setting to `True` to download the "
            "job script files to the execution dir.",
        )
    return []


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


async def fetch_pending_submissions() -> List[PendingJobSubmission]:
    """
    Retrieve a list of pending job_submissions.
    """
    with JobbergateApiError.handle_errors(
        "Failed to fetch pending job submissions",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.get("/jobbergate/job-submissions/agent/pending")
        response.raise_for_status()
        pending_job_submissions = [PendingJobSubmission(**pjs) for pjs in response.json().get("items", [])]

    logger.debug(f"Retrieved {len(pending_job_submissions)} pending job submissions")
    return pending_job_submissions


async def mark_as_submitted(job_submission_id: int, slurm_job_id: int):
    """
    Mark job_submission as submitted in the Jobbergate API.
    """
    logger.debug(f"Marking job submission {job_submission_id=} as submitted ({slurm_job_id=})")

    with JobbergateApiError.handle_errors(
        f"Could not mark job submission {job_submission_id} as submitted via the Jobbergate API",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.post(
            "jobbergate/job-submissions/agent/submitted",
            json=dict(
                id=job_submission_id,
                slurm_job_id=slurm_job_id,
            ),
        )
        response.raise_for_status()


async def mark_as_rejected(job_submission_id: int, report_message: str):
    """
    Mark job_submission as rejected in the Jobbergate API.
    """
    logger.debug(f"Marking job submission {job_submission_id} as rejected")

    with JobbergateApiError.handle_errors(
        f"Could not mark job submission {job_submission_id} as rejected via the Jobbergate API",
        do_except=log_error,
    ):
        response = await jobbergate_api_client.post(
            "jobbergate/job-submissions/agent/rejected",
            json=dict(
                id=job_submission_id,
                report_message=report_message,
            ),
        )
        response.raise_for_status()


async def submit_job_script(
    pending_job_submission: PendingJobSubmission,
    user_mapper: SlurmUserMapper,
) -> int:
    """
    Submit a Job Script to slurm via the Slurm REST API.

    :param: pending_job_submission: A job_submission with fields needed to submit.
    :returns: The ``slurm_job_id`` for the submitted job
    """

    async def _reject_handler(params: DoExceptParams):
        """
        Use for the ``do_except`` parameter of a ``handle_errors``.

        Logs the error and then invokes job rejection on the Jobbergate API.
        """
        log_error(params)
        await mark_as_rejected(pending_job_submission.id, params.final_message)

    async with handle_errors_async(
        "Username could not be resolved",
        raise_exc_class=JobSubmissionError,
        do_except=_reject_handler,
    ):
        email = pending_job_submission.owner_email
        mapper_class_name = user_mapper.__class__.__name__
        logger.debug(f"Fetching username for email {email} with mapper {mapper_class_name}")
        username = user_mapper[email]
        logger.debug(f"Using local slurm user {username} for job submission")

    submit_dir = pending_job_submission.execution_directory or SETTINGS.DEFAULT_SLURM_WORK_DIR
    sbatch_handler = SbatchHandler(
        username=username,
        sbatch_path=SETTINGS.SBATCH_PATH,
        scontrol_path=SETTINGS.SCONTROL_PATH,
        submission_directory=submit_dir,
    )

    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        async with handle_errors_async(
            "Error processing job-script files",
            raise_exc_class=JobSubmissionError,
            do_except=_reject_handler,
        ):
            logger.debug(f"Processing submission files for job submission {pending_job_submission.id}")
            supporting_files = await process_supporting_files(pending_job_submission, tmp_dir_path)

            logger.debug(f"Fetching job script for job submission {pending_job_submission.id}")
            job_script = await get_job_script_file(pending_job_submission, tmp_dir_path)

            sbatch_handler.create_submission_directory()
            job_script_final = sbatch_handler.copy_file_to_submission_directory(job_script)
            for file in supporting_files:
                sbatch_handler.copy_file_to_submission_directory(file)

    async with handle_errors_async(
        "Failed to submit job to slurm",
        raise_exc_class=JobSubmissionError,
        do_except=_reject_handler,
    ):
        logger.debug(f"Submitting job script for job submission {pending_job_submission.id}")
        slurm_job_id = sbatch_handler.run(job_script_final)

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
