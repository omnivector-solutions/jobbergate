from __future__ import annotations

import asyncio
import os
import pwd
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from tempfile import TemporaryDirectory

from buzz import DoExceptParams, handle_errors_async
from jobbergate_core.tools.sbatch import (
    InfoHandler,
    SubmissionHandler,
    SubprocessHandler,
    inject_sbatch_params,
)
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.jobbergate.constants import FileType
from jobbergate_agent.jobbergate.pagination import fetch_paginated_result
from jobbergate_agent.jobbergate.schemas import JobScriptFile, PendingJobSubmission, SlurmJobData
from jobbergate_agent.jobbergate.update import fetch_job_data
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, JobSubmissionError
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
    safe_filename = Path(filename).name
    local_script_path = submit_dir / safe_filename
    local_script_path.write_text(file_content, encoding="utf-8")

    logger.debug(f"Copied file to {local_script_path}")
    return local_script_path


async def process_supporting_files(pending_job_submission: PendingJobSubmission, submit_dir: Path) -> list[Path]:
    """
    Process the submission support files.

    Write the support files to the submit_dir if WRITE_SUBMISSION_FILES is set to True.
    Reject the submission if there are support files with WRITE_SUBMISSION_FILES set to False.
    """
    supporting_files = [file for file in pending_job_submission.job_script.files if file.file_type == FileType.SUPPORT]

    if not supporting_files:
        return []
    elif supporting_files and not SETTINGS.WRITE_SUBMISSION_FILES:
        logger.debug(f"Can't write files for submission {pending_job_submission.id}")
        raise JobSubmissionError(
            "Job submission rejected. The submission has supporting files that can't be downloaded to "
            "the execution dir. Set `WRITE_SUBMISSION_FILES` setting to `True` to download the "
            "job script files to the execution dir.",
        )
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


async def get_job_script_file(pending_job_submission: PendingJobSubmission, submit_dir: Path) -> Path:
    """Get the job script file from the backend."""
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

    if pending_job_submission.sbatch_arguments:
        job_script = inject_sbatch_params(
            job_script, pending_job_submission.sbatch_arguments, "Sbatch params injected at submission time"
        )

    return await write_submission_file(job_script, job_script_file.filename, submit_dir)


async def fetch_pending_submissions() -> list[PendingJobSubmission]:
    """
    Retrieve a list of pending job_submissions.
    """
    with JobbergateApiError.handle_errors("Failed to fetch pending job submissions", do_except=log_error):
        results = await fetch_paginated_result(
            url="/jobbergate/job-submissions/agent/pending",
            base_model=PendingJobSubmission,
        )

    logger.debug(f"Retrieved {len(results)} pending job submissions")
    return results


async def mark_as_submitted(job_submission_id: int, slurm_job_id: int, slurm_job_data: SlurmJobData):
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
                slurm_job_state=slurm_job_data.job_state,
                slurm_job_info=slurm_job_data.job_info,
                slurm_job_state_reason=slurm_job_data.state_reason,
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


@dataclass
class SubprocessAsUserHandler(SubprocessHandler):
    """Subprocess handler that runs as a given user."""

    username: str

    def __post_init__(self):
        pwan = pwd.getpwnam(self.username)
        self.uid = pwan.pw_uid
        self.gid = pwan.pw_gid

    def run(self, *args, **kwargs) -> CompletedProcess:
        kwargs.update(user=self.uid, group=self.gid, env={})
        # Tests indicate that the change on the working directory precedes the change of user on the subprocess.
        # With that, the user running the agent can face permission denied errors on cwd,
        # depending on the setting on the filesystem and permissions on the directory.
        # To avoid this, we change the working directory after changing to the submitter user using preexec_fn.
        if cwd := kwargs.pop("cwd", None):
            kwargs["preexec_fn"] = lambda: os.chdir(cwd)
        return super().run(*args, **kwargs)


def validate_submit_dir(submit_dir: Path, subprocess_handler: SubprocessAsUserHandler) -> None:
    """
    Validate the submission directory.

    The directory must exist and be writable by the user, so this verification is delegated to the subprocess
    handler as the user that will run the sbatch command.

    This is needed since `submit_dir.exists()` would run as the agent user, which may face permission errors.
    """
    if not submit_dir.is_absolute():
        raise ValueError("Execution directory must be an absolute path")
    try:
        subprocess_handler.run(cmd=("test", "-d", submit_dir.as_posix()))
        subprocess_handler.run(cmd=("test", "-w", submit_dir.as_posix()))
    except RuntimeError as e:
        raise ValueError("Execution directory does not exist or is not writable by the user") from e


async def submit_job_script(
    pending_job_submission: PendingJobSubmission,
    user_mapper: SlurmUserMapper,
) -> int:
    """
    Submit a Job Script to slurm via the sbatch command.

    Args:
        pending_job_submission: A job_submission with fields needed to submit.

    Returns:
        The ``slurm_job_id`` for the submitted job
    """
    logger.debug(f"Submitting {pending_job_submission}")

    async def _reject_handler(params: DoExceptParams) -> None:
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
        logger.debug(f"Fetching username for email '{email}' with mapper {mapper_class_name}")
        username = user_mapper[email]
        logger.debug(f"Using local slurm user '{username}' for job submission")
        subprocess_handler = SubprocessAsUserHandler(username)

    submit_dir = pending_job_submission.execution_directory or Path(
        SETTINGS.DEFAULT_SLURM_WORK_DIR.format(username=username)
    )
    async with handle_errors_async(
        "Execution directory is invalid", raise_exc_class=JobSubmissionError, do_except=_reject_handler
    ):
        validate_submit_dir(submit_dir, subprocess_handler)

    sbatch_handler = SubmissionHandler(
        sbatch_path=SETTINGS.SBATCH_PATH,
        submission_directory=submit_dir,
        subprocess_handler=subprocess_handler,
    )

    async with handle_errors_async(
        "Error processing job-script files", raise_exc_class=JobSubmissionError, do_except=_reject_handler
    ):
        logger.debug(f"Processing submission files for job submission {pending_job_submission.id}")
        with TemporaryDirectory(prefix=f"jobbergate-submission-{pending_job_submission.id}-") as tmp_dir:
            tmp_dir_path = Path(tmp_dir)

            supporting_files = await process_supporting_files(pending_job_submission, tmp_dir_path)

            logger.debug(f"Fetching job script for job submission {pending_job_submission.id}")
            job_script = await get_job_script_file(pending_job_submission, tmp_dir_path)

            if SETTINGS.WRITE_SUBMISSION_FILES:
                job_script = sbatch_handler.copy_file_to_submission_directory(job_script)
                for file in supporting_files:
                    sbatch_handler.copy_file_to_submission_directory(file)

    async with handle_errors_async(
        "Failed to submit job to slurm",
        raise_exc_class=JobSubmissionError,
        do_except=_reject_handler,
    ):
        logger.debug(f"Submitting job script for job submission {pending_job_submission.id}")
        slurm_job_id = sbatch_handler.submit_job(job_script)

    return slurm_job_id


async def submit_pending_jobs() -> None:
    """
    Submit all pending jobs and update them with ``SUBMITTED`` status and slurm_job_id.
    """
    logger.debug("Started submitting pending jobs...")

    info_handler = InfoHandler(scontrol_path=SETTINGS.SCONTROL_PATH)

    logger.debug("Building user-mapper")
    user_mapper = manufacture()

    logger.debug("Fetching pending jobs...")
    pending_job_submissions = await fetch_pending_submissions()

    for pending_job_submission in pending_job_submissions:
        logger.debug(f"Submitting pending job_submission {pending_job_submission.id}")
        with JobSubmissionError.handle_errors(
            f"Failed to submit pending job_submission {pending_job_submission.id}...skipping to next pending job",
            do_except=log_error,
            do_else=lambda: logger.debug(f"Finished submitting pending job_submission {pending_job_submission.id}"),
            re_raise=False,
        ):
            cache_file = SETTINGS.CACHE_DIR / f"{pending_job_submission.id}.slurm_job_id"
            if cache_file.exists():
                logger.debug(f"Found cache file for job submission {pending_job_submission.id}")
                slurm_job_id = int(cache_file.read_text())
            else:
                slurm_job_id = await submit_job_script(pending_job_submission, user_mapper)
                cache_file.write_text(str(slurm_job_id))

            slurm_job_data: SlurmJobData = await fetch_job_data(slurm_job_id, info_handler)

            await mark_as_submitted(pending_job_submission.id, slurm_job_id, slurm_job_data)
            cache_file.unlink(missing_ok=True)

    logger.debug("...Finished submitting pending jobs")
