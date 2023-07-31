"""
Router for the JobSubmission resource.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import status
from fastapi_pagination import Page
from loguru import logger

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.dependecies import file_services, secure_services
from jobbergate_api.apps.job_scripts.services import crud_service as script_crud_service
from jobbergate_api.apps.job_scripts.services import file_service as script_file_service
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.properties_parser import get_job_properties_from_job_script
from jobbergate_api.apps.job_submissions.schemas import (
    ActiveJobSubmission,
    JobSubmissionAgentUpdateRequest,
    JobSubmissionCreateRequest,
    JobSubmissionResponse,
    JobSubmissionUpdateRequest,
    PendingJobSubmission,
)
from jobbergate_api.apps.job_submissions.services import crud_service
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.email_notification import notify_submission_rejected
from jobbergate_api.storage import SecureSession

router = APIRouter(prefix="/job-submissions", tags=["Job Submissions"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(file_services(script_file_service))],
)
async def job_submission_create(
    create_request: JobSubmissionCreateRequest,
    secure_session: SecureSession = Depends(
        secure_services(
            Permissions.JOB_SUBMISSIONS_EDIT,
            services=[crud_service, script_crud_service, script_file_service],
        )
    ),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    logger.debug(f"Creating job submissions with {create_request=}")

    if secure_session.identity_payload.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )

    client_id = create_request.client_id or secure_session.identity_payload.client_id
    if client_id is None:
        message = "Could not find a client_id in the request body or auth token."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    create_request.client_id = client_id

    base_job_script = await script_crud_service.get(create_request.job_script_id)

    job_script_files = [f for f in base_job_script.files if f.file_type == FileType.ENTRYPOINT]

    if len(job_script_files) != 1:
        message = "Job script {} has {} entrypoint files, one and only one is required".format(
            create_request.job_script_id, len(job_script_files)
        )
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    main_file_content = await script_file_service.get_file_content(job_script_files[0])
    new_execution_parameters = get_job_properties_from_job_script(
        main_file_content.decode(), **create_request.execution_parameters.dict(exclude_unset=True)
    )
    create_request.execution_parameters = new_execution_parameters

    new_job_submission = await crud_service.create(
        **create_request.dict(exclude_unset=True),
        owner_email=secure_session.identity_payload.email,
        status=JobSubmissionStatus.CREATED,
    )
    return new_job_submission


@router.get(
    "/{id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(secure_services(Permissions.JOB_SUBMISSIONS_VIEW, services=[crud_service]))],
)
async def job_submission_get(id: int = Path(...)):
    """Return the job_submission given it's id."""
    logger.debug(f"Getting job submission {id=}")
    return await crud_service.get(id)


@router.get(
    "",
    description="Endpoint to list job_submissions",
    response_model=Page[JobSubmissionResponse],
)
async def job_submission_get_list(
    user_only: bool | None = Query(False),
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
    search: str | None = Query(None),
    sort_field: str | None = Query(None),
    sort_ascending: bool = Query(True),
    from_job_script_id: int
    | None = Query(
        None,
        description="Filter job-submissions by the job-script-id they were created from.",
    ),
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_VIEW, services=[crud_service])
    ),
):
    """List job_submissions for the authenticated user."""
    logger.debug("Fetching job submissions")

    list_kwargs: dict[str, Any] = dict(
        search=search,
        sort_field=sort_field,
        sort_ascending=sort_ascending,
    )

    if user_only:
        list_kwargs["owner_email"] = secure_session.identity_payload.email
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

    return await crud_service.paginated_list(**list_kwargs)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
)
async def job_submission_delete(
    id: int = Path(..., description="id of the job submission to delete"),
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, services=[crud_service])
    ),
):
    """Delete job_submission given its id."""
    logger.info(f"Deleting job submission {id=}")
    await crud_service.get_ensure_ownership(id, secure_session.identity_payload.email)
    await crud_service.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionResponse,
)
async def job_submission_update(
    update_params: JobSubmissionUpdateRequest,
    id: int = Path(),
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, services=[crud_service])
    ),
):
    """Update a job_submission given its id."""
    logger.debug(f"Updating {id=} with {update_params=}")
    await crud_service.get_ensure_ownership(id, secure_session.identity_payload.email)
    return await crud_service.update(id, **update_params.dict(exclude_unset=True))


# The "agent" routes are used for agents to fetch pending job submissions and update their statuses
@router.put(
    "/agent/{id}",
    status_code=200,
    description="Endpoint for an agent to update the status of a job_submission",
    response_model=JobSubmissionResponse,
    tags=["Agent"],
)
async def job_submission_agent_update(
    update_params: JobSubmissionAgentUpdateRequest,
    id: int = Path(),
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_EDIT, services=[crud_service])
    ),
):
    """
    Update a job_submission with a new status.

    Make a put request to this endpoint with the new status to update a job_submission.
    """
    logger.debug(f"Agent is requesting to update {id=}")

    await crud_service.get_ensure_client_id(id, secure_session.identity_payload.client_id)

    logger.info(
        f"Setting status to: {update_params.status} "
        f"for job_submission: {id} "
        f"on client_id: {secure_session.identity_payload.client_id}"
    )

    job_submission = await crud_service.update(id, **update_params.dict(exclude_unset=True))

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
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_VIEW, services=[crud_service])
    ),
):
    """Get a list of pending job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of pending job submissions")

    client_id = secure_session.identity_payload.client_id
    if client_id is None:
        message = "Access token does not contain a client_id. Cannot fetch pending submissions"
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    logger.info(f"Fetching newly created job_submissions for client_id: {client_id}")

    return await crud_service.paginated_list(
        status=JobSubmissionStatus.CREATED,
        client_id=client_id,
        eager_join=True,
    )


@router.get(
    "/agent/active",
    description="Endpoint to list active job_submissions for the requesting client",
    response_model=Page[ActiveJobSubmission],
    tags=["Agent"],
)
async def job_submissions_agent_active(
    secure_session: SecureSession = Depends(
        secure_services(Permissions.JOB_SUBMISSIONS_VIEW, services=[crud_service])
    ),
):
    """Get a list of active job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of active job submissions")

    client_id = secure_session.identity_payload.client_id
    if client_id is None:
        logger.error("Access token does not contain a client_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token does not contain a client_id. Cannot fetch pending submissions",
        )

    logger.info(f"Fetching active job_submissions for client_id: {client_id}")

    pages = await crud_service.paginated_list(
        status=JobSubmissionStatus.SUBMITTED,
        client_id=client_id,
    )
    return pages
