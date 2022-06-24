"""
Provide tool functions for working with Job Submission data
"""

from pathlib import Path
from typing import Optional, cast

from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobSubmissionCreateRequestData, JobSubmissionResponse
from jobbergate_cli.subapps.clusters.tools import validate_client_id


def create_job_submission(
    jg_ctx: JobbergateContext,
    job_script_id: int,
    name: str,
    description: Optional[str] = None,
    client_id: Optional[str] = None,
    execution_directory: Optional[Path] = None,
) -> JobSubmissionResponse:
    """
    Create a Job Submission from the given Job Script.

    :param: jg_ctx:              The JobbergateContext. Used to retrieve the client for requests
                                 and the email of the submitting user
    :param: job_script_id:       The ``id`` of the Job Script to submit to Slurm
    :param: name:                The name to attach to the Job Submission
    :param: description:         An optional description that may be added to the Job Submission
    :param: client_id:           An optional client_id for the cluster where the job should be executed,
                                 If left off, it will default to the client_id where this CLI is deployed.
                                 This field is called (in the code) ``client_id`` even though it is presented to the
                                 user as a name field. Armada uses textual, human-readable, parameterized names for the
                                 cluster clients.
                                 This value must appear in the available cluster names provided by the cluster-api.
    :param: execution_directory: An optional directory where the job should be executed. If provided as a relative path,
                                 it will be constructed as an absolute path relative to the current working directory.
    :returns: The Job Submission data returned by the API after creating the new Job Submission
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None, "jg_ctx.client is uninitialized"
    assert jg_ctx.persona is not None, "jg_ctx.persona is uninitialized"

    if client_id is None:
        client_id = jg_ctx.persona.identity_data.client_id
    validate_client_id(jg_ctx, client_id)

    job_submission_data = JobSubmissionCreateRequestData(
        job_submission_name=name,
        job_submission_description=description,
        job_script_id=job_script_id,
        client_id=client_id,
    )

    if execution_directory is not None:
        if not execution_directory.is_absolute():
            execution_directory = Path.cwd() / execution_directory
        execution_directory.resolve()
        job_submission_data.execution_directory = execution_directory

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
