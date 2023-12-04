"""
Provide tool functions for working with Job Submission data
"""

import re
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional, cast

from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.constants import FileType
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobSubmissionCreateRequestData, JobSubmissionResponse
from jobbergate_cli.subapps.job_scripts.tools import download_job_script_files, validate_parameter_file


def sbatch_run(filename: str, *argv) -> int:
    """Execute Job Submission using sbatch and returns slurm id."""

    if settings.SBATCH_PATH is None or not settings.SBATCH_PATH.exists():
        raise Abort(
            "The path to the sbatch executable is not set or does not exist. "
            "Please set the SBATCH_PATH environment to allow on-site job submissions.",
            subject="sbatch error",
            support=False,
        )

    cmd = [settings.SBATCH_PATH.as_posix(), filename, *argv]
    logger.debug(f"Executing: {' '.join(cmd)}")
    p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output_raw, err_raw = p.communicate(b"sbatch output")

    output = output_raw.decode("utf-8")
    err = err_raw.decode("utf-8")
    rc = p.returncode

    logger.debug("Job submission output: {}", output)
    logger.debug("Job submission return code: {}", rc)

    if rc != 0:
        logger.error("Job submission error: {}", err)
        raise Abort(f"Failed to execute submission with error: {err}", subject="sbatch error", support=False)

    match = re.search(r"^Submitted batch job (\d+)", output)

    if match is None:
        raise Abort(f"Failed to parse slurm job id from {output=}", subject="sbatch error", support=False)

    slurm_job_id = int(match.group(1))
    logger.info("Job submission successful. Slurm job id: {}", slurm_job_id)
    return slurm_job_id


def create_job_submission(
    jg_ctx: JobbergateContext,
    job_script_id: int,
    name: str,
    description: Optional[str] = None,
    cluster_name: Optional[str] = None,
    execution_directory: Optional[Path] = None,
    execution_parameters_file: Optional[Path] = None,
    download: bool = False,
) -> JobSubmissionResponse:
    """
    Create a Job Submission from the given Job Script.

    :param: jg_ctx:                    The JobbergateContext. Used to retrieve the client for requests
                                       and the email of the submitting user
    :param: job_script_id:             The ``id`` of the Job Script to submit to Slurm
    :param: name:                      The name to attach to the Job Submission
    :param: description:               An optional description that may be added to the Job Submission
    :param: cluster_name:              An optional cluster_name for the cluster where the job should be executed,
                                       If left off, it will default to the DEFAULT_CLUSTER_NAME from the settings.
                                       If no default is set, an exception will be raised.
    :param: execution_directory:       An optional directory where the job should be executed. If provided as a
                                       relative path, it will be constructed as an absolute path relative to
                                       the current working directory.
    :param: execution_parameters_file: An optional file containing the execution parameters for the job.

    :returns: The Job Submission data returned by the API after creating the new Job Submission
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None, "jg_ctx.client is uninitialized"

    if cluster_name is None:
        cluster_name = settings.DEFAULT_CLUSTER_NAME

    Abort.require_condition(
        cluster_name is not None,
        "No cluster name supplied and no default exists. Cannot submit to an unknown cluster!",
        raise_kwargs=dict(
            subject="No cluster Name",
            support=True,
        ),
    )

    Abort.require_condition(
        settings.SBATCH_PATH is None or execution_parameters_file is None,
        "Execution parameters file is not compatible with on-site job submissions",
        raise_kwargs=dict(subject="Job Submission Error", support=False),
    )

    if execution_directory is None:
        execution_directory = Path.cwd()
    if not execution_directory.is_absolute():
        execution_directory = execution_directory.resolve()

    job_submission_data = JobSubmissionCreateRequestData(
        name=name,
        description=description,
        job_script_id=job_script_id,
        cluster_name=cluster_name,
        execution_directory=execution_directory,
    )

    if execution_parameters_file is not None:
        job_submission_data.execution_parameters = validate_parameter_file(execution_parameters_file)

    if download or settings.SBATCH_PATH is not None:
        job_script_files = download_job_script_files(job_script_id, jg_ctx, Path.cwd())

    if settings.SBATCH_PATH is None:
        logger.info("Creating job submission in remote mode")
    else:
        logger.info("Creating job submission in on-site mode")

        entrypoint_file = [f for f in job_script_files if f.file_type == FileType.ENTRYPOINT]

        Abort.require_condition(
            len(entrypoint_file) == 1,
            "There should be exactly one entrypoint file in the parent job script",
            raise_kwargs=dict(subject="Job Script Error"),
        )

        filename = entrypoint_file[0].filename
        slurm_id = sbatch_run(filename, name)
        job_submission_data.slurm_job_id = slurm_id

    result = cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            "/jobbergate/job-submissions",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job submission",
            support=True,
            request_model=job_submission_data,
            response_model_cls=JobSubmissionResponse,
        ),
    )
    return result


def fetch_job_submission_data(
    jg_ctx: JobbergateContext,
    job_submission_id: int,
) -> JobSubmissionResponse:
    """
    Retrieve a job submission from the API by ``id``
    """
    # Make static type checkers happy
    assert jg_ctx.client is not None, "Client is uninitialized"

    return cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            f"/jobbergate/job-submissions/{job_submission_id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job submission {job_submission_id} from API",
            support=True,
            response_model_cls=JobSubmissionResponse,
        ),
    )
