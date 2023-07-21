"""
Router for the JobSubmission resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import Response as FastAPIResponse
from fastapi import status
from fastapi_pagination import Page
from loguru import logger
from sqlalchemy.orm import joinedload

from jobbergate_api.apps.constants import FileType
from jobbergate_api.apps.job_scripts.dependecies import job_script_files_service, job_script_service
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.dependecies import job_submission_service
from jobbergate_api.apps.job_submissions.properties_parser import get_job_properties_from_job_script
from jobbergate_api.apps.job_submissions.schemas import (
    ActiveJobSubmission,
    JobSubmissionAgentUpdateRequest,
    JobSubmissionCreateRequest,
    JobSubmissionResponse,
    JobSubmissionUpdateRequest,
    PendingJobSubmission,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.apps.services import FileService, TableService
from jobbergate_api.email_notification import notify_submission_rejected
from jobbergate_api.security import IdentityClaims, guard

router = APIRouter(prefix="/job-submissions", tags=["Job Submissions"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionResponse,
)
async def job_submission_create(
    create_request: JobSubmissionCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT)),
    job_script_service: TableService = Depends(job_script_service),
    job_script_file_service: FileService = Depends(job_script_files_service),
    service: TableService = Depends(job_submission_service),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    logger.debug(f"Creating job submissions with {create_request=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The token payload does not contain an email",
        )
    client_id = create_request.client_id or identity_claims.client_id
    if client_id is None:
        message = "Could not find a client_id in the request body or auth token."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
    create_request.client_id = client_id

    base_job_script = await job_script_service.get(create_request.job_script_id)

    job_script_files = [f for f in base_job_script.files.values() if f.file_type == FileType.ENTRYPOINT]

    if len(job_script_files) != 1:
        message = "Job script {} has {} entrypoint files, one and only one is required".format(
            create_request.job_script_id, len(job_script_files)
        )
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    main_file_content = await job_script_file_service.get(job_script_files[0])
    new_execution_parameters = get_job_properties_from_job_script(
        main_file_content.decode(), **create_request.execution_parameters.dict(exclude_unset=True)
    )
    create_request.execution_parameters = new_execution_parameters

    new_job_submission = await service.create(
        **create_request.dict(exclude_unset=True),
        owner_email=identity_claims.email,
        status=JobSubmissionStatus.CREATED,
    )
    return new_job_submission


@router.get(
    "/{id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW))],
)
async def job_submission_get(
    id: int = Path(...),
    service: TableService = Depends(job_submission_service),
):
    """Return the job_submission given it's id."""
    logger.debug(f"Getting job submission {id=}")

    return await service.get(id)


@router.get(
    "",
    description="Endpoint to list job_submissions",
    response_model=Page[JobSubmissionResponse],
)
async def job_submission_list(
    user_only: Optional[bool] = Query(False),
    slurm_job_ids: Optional[str] = Query(
        None,
        description="Comma-separated list of slurm-job-ids to match active job_submissions",
    ),
    submit_status: Optional[JobSubmissionStatus] = Query(
        None,
        description="Limit results to those with matching status",
    ),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_ascending: bool = Query(True),
    from_job_script_id: Optional[int] = Query(
        None,
        description="Filter job-submissions by the job-script-id they were created from.",
    ),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW)),
    service: TableService = Depends(job_submission_service),
):
    """List job_submissions for the authenticated user."""
    logger.debug("Fetching job submissions")

    identity_claims = IdentityClaims.from_token_payload(token_payload)

    list_kwargs = dict(
        search=search,
        sort_field=sort_field,
        sort_ascending=sort_ascending,
    )

    if user_only:
        list_kwargs["owner_email"] = identity_claims.email
    if submit_status:
        list_kwargs["status"] = submit_status
    if from_job_script_id:
        list_kwargs["job_script_id"] = from_job_script_id
    if slurm_job_ids:
        try:
            job_ids = list(map(int, slurm_job_ids.split(",")))
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid slurm_job_ids param. Must be a comma-separated list of integers",
            )

        def custom_filter(table, query):
            return query.where(table.slurm_job_id.in_(job_ids))

        list_kwargs["custom_filter"] = custom_filter

    return await service.list(**list_kwargs)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT))],
)
async def job_submission_delete(
    id: int = Path(..., description="id of the job submission to delete"),
    service: TableService = Depends(job_submission_service),
):
    """Delete job_submission given its id."""
    logger.info(f"Deleting job submission {id=}")
    await service.delete(id)
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT))],
)
async def job_submission_update(
    update_params: JobSubmissionUpdateRequest,
    id: int = Path(),
    service: TableService = Depends(job_submission_service),
):
    """Update a job_submission given its id."""
    logger.debug(f"Updating {id=} with {update_params=}")
    await service.update(id, **update_params.dict(exclude_unset=True))
    return await service.get(id)


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
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT)),
    service: TableService = Depends(job_submission_service),
):
    """
    Update a job_submission with a new status.

    Make a put request to this endpoint with the new status to update a job_submission.
    """
    logger.debug(f"Agent is requesting to update {id=}")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.client_id is None:
        logger.error("Access token does not contain a client_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token does not contain a `client_id`. Cannot update job_submission",
        )

    logger.info(
        f"Setting status to: {update_params.status} "
        f"for job_submission: {id} "
        f"on client_id: {identity_claims.client_id}"
    )

    await service.update(id, **update_params.dict(exclude_unset=True))

    job_submission = await service.get(id)

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
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW)),
    service: TableService = Depends(job_submission_service),
):
    """Get a list of pending job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of pending job submissions")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.client_id is None:
        message = "Access token does not contain a `client_id`. Cannot fetch pending submissions"
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    logger.info(f"Fetching newly created job_submissions for client_id: {identity_claims.client_id}")

    def custom_filter(table, query):
        return query.options(joinedload(table.job_script))

    return await service.list(
        status=JobSubmissionStatus.CREATED,
        client_id=identity_claims.client_id,
        custom_filter=custom_filter,
    )


@router.get(
    "/agent/active",
    description="Endpoint to list active job_submissions for the requesting client",
    response_model=Page[ActiveJobSubmission],
    tags=["Agent"],
)
async def job_submissions_agent_active(
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW)),
    service: TableService = Depends(job_submission_service),
):
    """Get a list of active job submissions for the cluster-agent."""
    logger.debug("Agent is requesting a list of active job submissions")

    identity_claims = IdentityClaims.from_token_payload(token_payload)
    if identity_claims.client_id is None:
        logger.error("Access token does not contain a client_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token does not contain a `client_id`. Cannot fetch pending submissions",
        )

    logger.info(f"Fetching active job_submissions for client_id: {identity_claims.client_id}")

    return await service.list(
        status=JobSubmissionStatus.CREATED,
        client_id=identity_claims.client_id,
    )


def include_router(app):
    """Include the router for this module in the app."""
    app.include_router(router)
