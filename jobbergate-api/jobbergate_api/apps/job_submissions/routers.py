"""
Router for the JobSubmission resource.
"""
from buzz import handle_errors
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import status
from fastapi_pagination import Page
from loguru import logger

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependencies import SecureService, secure_services
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.properties_parser import get_job_properties_from_job_script
from jobbergate_api.apps.job_submissions.schemas import (
    ActiveJobSubmission,
    JobSubmissionAgentUpdateRequest,
    JobSubmissionCreateRequest,
    JobSubmissionDetailedView,
    JobSubmissionListView,
    JobSubmissionUpdateRequest,
    PendingJobSubmission,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.schemas import ListParams
from jobbergate_api.apps.services import ServiceError
from jobbergate_api.email_notification import notify_submission_rejected

router = APIRouter(prefix="/job-submissions", tags=["Job Submissions"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_create(
    create_request: JobSubmissionCreateRequest,
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, ensure_email=True)
    ),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    logger.debug(f"Creating job submissions with {create_request=}")

    client_id = create_request.client_id or secure_services.identity_payload.client_id
    if client_id is None:
        message = "Could not find a client_id in the request body or auth token."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    create_request.client_id = client_id

    base_job_script = await secure_services.crud.job_script.get(
        create_request.job_script_id, include_files=True
    )

    job_script_files = [f for f in base_job_script.files if f.file_type == FileType.ENTRYPOINT]

    if len(job_script_files) != 1:
        message = "Job script {} has {} entrypoint files, one and only one is required".format(
            create_request.job_script_id, len(job_script_files)
        )
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    if create_request.slurm_job_id is None:
        main_file_content = await secure_services.file.job_script.get_file_content(job_script_files[0])

        with handle_errors(
            "Failed to parse execution parameters from the job script",
            raise_exc_class=ServiceError,
            raise_kwargs=dict(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY),
        ):
            execution_parameters = get_job_properties_from_job_script(
                main_file_content.decode(), **create_request.execution_parameters.dict(exclude_unset=True)
            )

        create_request.execution_parameters = execution_parameters
        submission_status = JobSubmissionStatus.CREATED
    else:
        if create_request.execution_parameters.dict(exclude_unset=True):
            message = "Execution parameters are not allowed for on-site job submissions"
            logger.warning(message)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
        submission_status = JobSubmissionStatus.SUBMITTED

    new_job_submission = await secure_services.crud.job_submission.create(
        **create_request.dict(exclude_unset=True),
        owner_email=secure_services.identity_payload.email,
        status=submission_status,
    )
    return new_job_submission


@router.get(
    "/{id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_get(
    id: int = Path(...),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SUBMISSIONS_VIEW, commit=False)),
):
    """Return the job_submission given it's id."""
    logger.debug(f"Getting job submission {id=}")
    return await secure_services.crud.job_submission.get(id)


@router.get(
    "",
    description="Endpoint to list job_submissions",
    response_model=Page[JobSubmissionListView],
)
async def job_submission_get_list(
    list_params: ListParams = Depends(),
    slurm_job_ids: str
    | None = Query(
        None,
        description="Comma-separated list of slurm-job-ids to match active job_submissions",
    ),
    submit_status: JobSubmissionStatus
    | None = Query(
        None,
        description="Limit results to those with matching status",
    ),
    from_job_script_id: int
    | None = Query(
        None,
        description="Filter job-submissions by the job-script-id they were created from.",
    ),
    secure_services: SecureService = Depends(secure_services(Permissions.JOB_SUBMISSIONS_VIEW, commit=False)),
):
    """List job_submissions for the authenticated user."""
    logger.debug("Fetching job submissions")

    list_kwargs = list_params.dict(exclude_unset=True, exclude={"user_only", "include_archived"})

    if list_params.user_only:
        list_kwargs["owner_email"] = secure_services.identity_payload.email
    if submit_status:
        list_kwargs["status"] = submit_status
    if from_job_script_id:
        list_kwargs["job_script_id"] = from_job_script_id
    if slurm_job_ids:
        try:
            list_kwargs["filter_slurm_job_ids"] = [int(i) for i in slurm_job_ids.split(",")]
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid slurm_job_ids param. Must be a comma-separated list of integers",
            )

    return await secure_services.crud.job_submission.paginated_list(
        **list_kwargs,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
)
async def job_submission_delete(
    id: int = Path(..., description="id of the job submission to delete"),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, ensure_email=True)
    ),
):
    """Delete job_submission given its id."""
    logger.info(f"Deleting job submission {id=}")
    await secure_services.crud.job_submission.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    await secure_services.crud.job_submission.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionDetailedView,
)
async def job_submission_update(
    update_params: JobSubmissionUpdateRequest,
    id: int = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, ensure_email=True)
    ),
):
    """Update a job_submission given its id."""
    logger.debug(f"Updating {id=} with {update_params=}")
    await secure_services.crud.job_submission.get(
        id, ensure_attributes={"owner_email": secure_services.identity_payload.email}
    )
    return await secure_services.crud.job_submission.update(id, **update_params.dict(exclude_unset=True))


# The "agent" routes are used for agents to fetch pending job submissions and update their statuses
@router.put(
    "/agent/{id}",
    status_code=200,
    description="Endpoint for an agent to update the status of a job_submission",
    response_model=JobSubmissionDetailedView,
    tags=["Agent"],
)
async def job_submission_agent_update(
    update_params: JobSubmissionAgentUpdateRequest,
    id: int = Path(),
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, ensure_client_id=True)
    ),
):
    """
    Update a job_submission with a new status.

    Make a put request to this endpoint with the new status to update a job_submission.
    """
    logger.debug(f"Agent is requesting to update {id=}")

    logger.info(
        f"Setting status to: {update_params.status} "
        f"for job_submission: {id} "
        f"on client_id: {secure_services.identity_payload.client_id}"
    )
    await secure_services.crud.job_submission.get(
        id, ensure_attributes={"client_id": secure_services.identity_payload.client_id}
    )
    job_submission = await secure_services.crud.job_submission.update(
        id, **update_params.dict(exclude_unset=True)
    )

    if update_params.report_message and update_params.status == JobSubmissionStatus.REJECTED:
        notify_submission_rejected(id, update_params.report_message, job_submission.owner_email)

    return job_submission


@router.get(
    "/agent/pending",
    description="Endpoint to list pending job_submissions for the requesting client",
    response_model=Page[PendingJobSubmission],
    response_model_exclude_none=True,
    tags=["Agent"],
)
async def job_submissions_agent_pending(
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_VIEW, commit=False, ensure_client_id=True)
    ),
):
    """Get a list of pending job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of pending job submissions")

    client_id = secure_services.identity_payload.client_id

    logger.info(f"Fetching newly created job_submissions for {client_id=}")

    return await secure_services.crud.job_submission.paginated_list(
        status=JobSubmissionStatus.CREATED,
        client_id=client_id,
        include_files=True,
        include_parent=True,
    )


@router.get(
    "/agent/active",
    description="Endpoint to list active job_submissions for the requesting client",
    response_model=Page[ActiveJobSubmission],
    tags=["Agent"],
)
async def job_submissions_agent_active(
    secure_services: SecureService = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_VIEW, commit=False, ensure_client_id=True)
    ),
):
    """Get a list of active job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of active job submissions")

    client_id = secure_services.identity_payload.client_id

    logger.info(f"Fetching active job_submissions for {client_id=}")

    pages = await secure_services.crud.job_submission.paginated_list(
        status=JobSubmissionStatus.SUBMITTED,
        client_id=client_id,
    )
    return pages
