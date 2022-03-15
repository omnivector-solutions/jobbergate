"""
Provide tool functions for working with Job Submission data
"""

from typing import Optional, cast

from jobbergate_cli.requests import make_request
from jobbergate_cli.schemas import JobbergateContext, JobSubmissionResponse
from jobbergate_cli.schemas import JobbergateContext, JobSubmissionResponse


def create_job_submission(
    jg_ctx: JobbergateContext,
    job_script_id: int,
    name: str,
    description: Optional[str] = None,
) -> JobSubmissionResponse:
    """
    Creae a Job Submission from the given Job Script.

    :param: jg_ctx:        The JobbergateContext. Used to retrieve the client for requests
                           and the email of the submitting user
    :param: job_script_id: The ``id`` of the Job Script to submit to Slurm
    :param: name:          The name to attach to the Job Submission
    :param: description:   An optional description that may be added to the Job Submission
    :returns: The Job Submission data returned by the API after creating the new Job Submission
    """

    # Make static type checkers happy
    assert jg_ctx.client is not None, "jg_ctx.client is uninitialized"
    assert jg_ctx.persona is not None, "jg_ctx.persona is uninitialized"

    job_submission_data = dict(
        job_submission_name=name,
        job_submission_description=description,
        job_script_id=job_script_id,
    )

    result = cast(
        JobSubmissionResponse,
        make_request(
            jg_ctx.client,
            "/job-submissions",
            "POST",
            expected_status=201,
            abort_message="Couldn't create job submission",
            support=True,
            json=job_submission_data,
            response_model=JobSubmissionResponse,
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
            f"/job-submissions/{job_submission_id}",
            "GET",
            expected_status=200,
            abort_message=f"Couldn't retrieve job submission {job_submission_id} from API",
            support=True,
            response_model=JobSubmissionResponse,
        ),
    )
