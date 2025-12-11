from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from functools import cached_property, partial
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable, Coroutine

from buzz import DoExceptParams, handle_errors_async
from jobbergate_core.tools.sbatch import (
    InfoHandler,
    SubmissionHandler,
    inject_sbatch_params,
)
from loguru import logger

from jobbergate_agent.clients.cluster_api import backend_client as jobbergate_api_client
from jobbergate_agent.jobbergate.constants import FileType
from jobbergate_agent.jobbergate.pagination import fetch_paginated_result
from jobbergate_agent.jobbergate.schemas import JobScriptFile, PendingJobSubmission, SlurmJobData
from jobbergate_agent.jobbergate.update import fetch_job_data, SubprocessAsUserHandler
from jobbergate_agent.settings import SETTINGS
from jobbergate_agent.utils.exception import JobbergateApiError, JobSubmissionError
from jobbergate_agent.utils.logging import log_error
from jobbergate_agent.utils.user_mapper import manufacture
from jobbergate_agent.utils.plugin import get_plugin_manager, hookimpl, hookspec


async def retrieve_submission_file(file: JobScriptFile) -> str:
    """
    Get a submission file from the backend and return the decoded file content.
    """
    response = await jobbergate_api_client.get(file.path)
    response.raise_for_status()

    return response.content.decode("utf-8")


def write_submission_file(file_content: str, filename: str, submit_dir: Path) -> Path:
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
        asyncio.to_thread(write_submission_file, file_content, file.filename, submit_dir)
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

    return write_submission_file(job_script, job_script_file.filename, submit_dir)


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


def reject_handler(id: int) -> Callable[[DoExceptParams], Coroutine[Any, Any, None]]:
    async def helper(params: DoExceptParams) -> None:
        """
        Use for the ``do_except`` parameter of a ``handle_errors``.

        Logs the error and then invokes job rejection on the Jobbergate API.
        """
        log_error(params)
        await mark_as_rejected(id, params.final_message)

    return helper


async def submit_job_script(context: PendingJobSubmissionContext) -> int:
    """
    Submit a Job Script to slurm via the sbatch command.

    Args:
        pending_job_submission: A job_submission with fields needed to submit.

    Returns:
        The ``slurm_job_id`` for the submitted job
    """
    logger.debug(f"Submitting {context.data.id} job script to slurm...")
    do_except = reject_handler(context.data.id)

    async with handle_errors_async(
        "Execution directory is invalid", raise_exc_class=JobSubmissionError, do_except=do_except
    ):
        validate_submit_dir(context.submission_dir, context.subprocess_handler)

    async with handle_errors_async(
        "Error processing job-script files", raise_exc_class=JobSubmissionError, do_except=do_except
    ):
        logger.debug(f"Processing submission files for job submission {context.data.id}")
        with TemporaryDirectory(prefix=f"jobbergate-submission-{context.data.id}-") as tmp_dir:
            tmp_dir_path = Path(tmp_dir)

            supporting_files = await process_supporting_files(context.data, tmp_dir_path)

            logger.debug(f"Fetching job script for job submission {context.data.id}")
            job_script = await get_job_script_file(context.data, tmp_dir_path)

            if SETTINGS.WRITE_SUBMISSION_FILES:
                job_script = context.submission_handler.copy_file_to_submission_directory(job_script)
                for file in supporting_files:
                    context.submission_handler.copy_file_to_submission_directory(file)

    async with handle_errors_async(
        "Failed to submit job to slurm",
        raise_exc_class=JobSubmissionError,
        do_except=do_except,
    ):
        logger.debug(f"Submitting job script for job submission {context.data.id}")
        slurm_job_id = context.submission_handler.submit_job(job_script)

    return slurm_job_id


JobProcessStrategy = Callable[[], Coroutine[Any, Any, None]]
"""Type alias for job process strategy functions."""


async def empty_strategy() -> None:
    """An empty strategy that does nothing."""
    return None


@dataclass
class PendingJobSubmissionContext:
    """Context for pending job submission processing."""

    data: PendingJobSubmission
    username: str

    _slurm_job_id: int | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def submission_dir(self) -> Path:
        """The submission directory for the job submission."""
        return self.data.execution_directory or Path(SETTINGS.DEFAULT_SLURM_WORK_DIR.format(username=self.username))

    @property
    def is_submitted(self) -> bool:
        """Whether the job submission has been submitted to Slurm."""
        return self._slurm_job_id is not None

    @property
    def slurm_job_id(self) -> int:
        """The Slurm job ID for the job submission."""
        if self._slurm_job_id is None:
            raise ValueError("Slurm job ID has not been set yet")
        return self._slurm_job_id

    def set_slurm_job_id(self, slurm_job_id: int) -> None:
        """Set the Slurm job ID for the job submission."""
        self._slurm_job_id = slurm_job_id

    @cached_property
    def subprocess_handler(self) -> SubprocessAsUserHandler:
        """Subprocess handler for running commands as the submitter user."""
        return SubprocessAsUserHandler(self.username)

    @cached_property
    def info_handler(self) -> InfoHandler:
        """InfoHandler for fetching job info from Slurm."""
        return InfoHandler(scontrol_path=SETTINGS.SCONTROL_PATH)

    @cached_property
    def submission_handler(self) -> SubmissionHandler:
        """SubmissionHandler for submitting jobs to Slurm."""
        return SubmissionHandler(
            sbatch_path=SETTINGS.SBATCH_PATH,
            submission_directory=self.submission_dir,
            subprocess_handler=self.subprocess_handler,
        )

    @cached_property
    def slurm_job_data(self) -> SlurmJobData:
        """Fetch the Slurm job data for the job submission."""
        return fetch_job_data(self.slurm_job_id, self.info_handler)


class PendingSubmissionPluginSpecs:
    """Hook specifications for pending job processing plugins."""

    @hookspec
    def pending_submission(self, context: PendingJobSubmissionContext) -> JobProcessStrategy:
        return empty_strategy


@hookimpl(specname="pending_submission", trylast=True)
def pending_job_submission_strategy(context: PendingJobSubmissionContext) -> JobProcessStrategy:
    """Get the job processing strategy for a pending job submission."""

    async def helper() -> None:
        """Helper function to process the pending job submission."""
        logger.debug(f"Submitting pending job_submission {context.data.id}")

        cache_file = SETTINGS.CACHE_DIR / f"{context.data.id}.slurm_job_id"
        if cache_file.exists():
            logger.debug(f"Found cache file for job submission {context.data.id}")
            slurm_job_id = int(cache_file.read_text())
        else:
            slurm_job_id = await submit_job_script(context)
            cache_file.write_text(str(slurm_job_id))

        context.set_slurm_job_id(slurm_job_id)

        await mark_as_submitted(context.data.id, slurm_job_id, context.slurm_job_data)
        cache_file.unlink(missing_ok=True)

    return helper


pending_submission_plugin_manager = partial(
    get_plugin_manager,
    "pending_submission",
    hookspec_class=PendingSubmissionPluginSpecs,
    register=[sys.modules[__name__]],
)


async def submit_pending_jobs() -> None:
    """
    Submit all pending jobs and update them with ``SUBMITTED`` status and slurm_job_id.
    """
    logger.debug("Started submitting pending jobs...")
    user_mapper = manufacture()
    plugin_manager = pending_submission_plugin_manager()
    pending_job_submissions = await fetch_pending_submissions()
    for pending_job in pending_job_submissions:
        try:
            username = user_mapper[pending_job.owner_email]
        except KeyError:
            message = "Username could not be resolved from owner email"
            logger.error(f"{message} for job submission {pending_job.id}")
            await mark_as_rejected(pending_job.id, message)
            continue

        try:
            for strategy in plugin_manager.hook.pending_submission(
                context=PendingJobSubmissionContext(pending_job, username)
            ):
                await strategy()
            logger.debug("Finished handling pending job_submission {}", pending_job.id)
        except Exception as e:
            logger.error("Error processing pending job submission {}: {}", pending_job.id, e)

    logger.debug("...Finished submitting pending jobs")
