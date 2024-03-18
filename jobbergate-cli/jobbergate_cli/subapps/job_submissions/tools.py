"""
Provide tool functions for working with Job Submission data
"""

from pathlib import Path
from typing import Optional, cast

from jobbergate_core.tools.sbatch import SubmissionHandler, inject_sbatch_params
from loguru import logger

from jobbergate_cli.config import settings
from jobbergate_cli.constants import FileType
from jobbergate_cli.exceptions import Abort
from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobSubmissionCreateRequestData, JobSubmissionResponse
from jobbergate_cli.subapps.job_scripts.tools import download_job_script_files


def _map_cluster_name(
    jg_ctx: JobbergateContext,
    base_cluster_name: str,
):
    """
    Injects the organization name into the cluster name for multi-tenancy mode.

    If the organization is undefined (multi-tenancy is disabled) or the cluster_name already includes the
    organization_id, use the base_cluster_name.
    """
    # Make static type checkers happy
    assert jg_ctx.persona is not None, "jg_ctx.persona is uninitialized"

    org_id = jg_ctx.persona.identity_data.organization_id
    if org_id is None or base_cluster_name.endswith(org_id):
        return base_cluster_name

    return f"{base_cluster_name}-{jg_ctx.persona.identity_data.organization_id}"


def create_job_submission(
    jg_ctx: JobbergateContext,
    job_script_id: int,
    name: str,
    description: Optional[str] = None,
    cluster_name: Optional[str] = None,
    execution_directory: Optional[Path] = None,
    sbatch_arguments: Optional[list[str]] = None,
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
    :param: sbatch_arguments: An optional list of strings containing additional arguments to pass to sbatch

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

    if execution_directory is None:
        execution_directory = Path.cwd()
    if not execution_directory.is_absolute():
        execution_directory = execution_directory.resolve()

    job_submission_data = JobSubmissionCreateRequestData(
        name=name,
        description=description,
        job_script_id=job_script_id,
        cluster_name=_map_cluster_name(jg_ctx, cluster_name),
        execution_directory=execution_directory,
        sbatch_arguments=sbatch_arguments,
    )

    if download or settings.SBATCH_PATH is not None:
        job_script_files = download_job_script_files(job_script_id, jg_ctx, execution_directory)

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
        job_script_path = execution_directory / entrypoint_file[0].filename

        if sbatch_arguments:
            job_script_content = job_script_path.read_text()
            job_script_content = inject_sbatch_params(
                job_script_content, sbatch_arguments, "Injected at submission time by Jobbergate CLI"
            )
            job_script_path.write_text(job_script_content)

        try:
            sbatch_handler = SubmissionHandler(
                sbatch_path=settings.SBATCH_PATH,
                submission_directory=execution_directory,
            )
            slurm_id = sbatch_handler.submit_job(job_script_path)
        except Exception as e:
            raise Abort(
                "Failed to submit job to Slurm",
                raise_kwargs=dict(
                    subject="Slurm Submission Error",
                    support=True,
                ),
            ) from e
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
