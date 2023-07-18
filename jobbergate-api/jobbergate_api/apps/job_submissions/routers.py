"""
Router for the JobSubmission resource.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.future import select

from jobbergate_api.apps.applications.models import applications_table
from jobbergate_api.apps.job_scripts.job_script_files import JobScriptFiles
from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.constants import JobSubmissionStatus
from jobbergate_api.apps.job_submissions.models import (
    job_submissions_table,
    searchable_fields,
    sortable_fields,
)
from jobbergate_api.apps.job_submissions.properties_parser import get_job_properties_from_job_script
from jobbergate_api.apps.job_submissions.schemas import (
    ActiveJobSubmission,
    JobSubmissionCreateRequest,
    JobSubmissionResponse,
    JobSubmissionUpdateRequest,
    PendingJobSubmission,
)
from jobbergate_api.apps.permissions import Permissions, check_owner
from jobbergate_api.config import settings
from jobbergate_api.email_notification import notify_submission_rejected
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.storage import (
    INTEGRITY_CHECK_EXCEPTIONS,
    SecureSession,
    fetch_data,
    fetch_instance,
    render_sql,
    search_clause,
    secure_session,
    sort_clause,
)

router = APIRouter()


async def _fetch_job_submission_by_id(
    secure_session: SecureSession,
    job_submission_id: int,
) -> JobSubmissionResponse:
    """
    Fetch a job_submission from the database by its id.
    """
    return await fetch_instance(
        secure_session.session, job_submission_id, job_submissions_table, JobSubmissionResponse
    )


def _get_override_bucket_name(secure_session: SecureSession) -> Optional[str]:
    """
    Get the override_bucket_name based on organization_id if multi-tenancy is enabled.
    """
    if settings.MULTI_TENANCY_ENABLED:
        return secure_session.identity_payload.organization_id
    return None


@router.post(
    "/job-submissions",
    status_code=201,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionResponse,
)
async def job_submission_create(
    job_submission: JobSubmissionCreateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_EDIT)),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    logger.debug(f"Creating {job_submission=}")

    client_id = job_submission.client_id or secure_session.identity_payload.client_id
    if client_id is None:
        message = "Could not find a client_id in the request body or auth token."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    new_job_submission_data: Dict[str, Any] = dict(
        **job_submission.dict(exclude_unset=True),
        job_submission_owner_email=secure_session.identity_payload.email,
        status=JobSubmissionStatus.CREATED,
    )
    if job_submission.client_id is None:
        new_job_submission_data.update(client_id=client_id)

    exec_dir = new_job_submission_data.pop("execution_directory", None)
    if exec_dir is not None:
        new_job_submission_data.update(execution_directory=str(exec_dir))

    job_script_data = await fetch_data(
        secure_session.session,
        job_submission.job_script_id,
        job_scripts_table,
        trace_query=True,
    )

    try:
        job_properties = get_job_properties_from_job_script(
            job_submission.job_script_id,
            _get_override_bucket_name(secure_session=secure_session),
            **job_submission.execution_parameters.dict(exclude_unset=True),
        )
        new_job_submission_data["execution_parameters"] = job_properties.dict(exclude_unset=True)
    except Exception as e:
        message = f"Error extracting execution parameters from job script: {str(e)}"
        logger.error(message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    logger.debug("Inserting job-submission")

    try:
        insert_query = job_submissions_table.insert().returning(job_submissions_table)
        logger.trace(f"job_submissions insert_query = {render_sql(secure_session.session, insert_query)}")
        raw_result = await secure_session.session.execute(insert_query, new_job_submission_data)

    except INTEGRITY_CHECK_EXCEPTIONS as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    new_job_submission = JobSubmissionResponse.from_orm(raw_result.one())
    new_job_submission.job_script_name = job_script_data.job_script_name
    logger.debug(f"Job-submission created: {new_job_submission=}")

    return new_job_submission


@router.get(
    "/job-submissions/{job_submission_id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionResponse,
)
async def job_submission_get(
    job_submission_id: int = Query(...),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_VIEW)),
):
    """
    Return the job_submission given it's id.
    """
    logger.debug(f"Getting {job_submission_id=}")

    query = (
        select(job_submissions_table.c, job_scripts_table.c.job_script_name)
        .where(job_submissions_table.c.id == job_submission_id)
        .join(
            job_scripts_table,
            job_scripts_table.columns.id == job_submissions_table.columns.job_script_id,
            isouter=True,
        )
    )
    logger.trace(f"query = {render_sql(secure_session.session, query)}")
    raw_result = await secure_session.session.execute(query)
    job_submission_data = raw_result.one_or_none()

    if not job_submission_data:
        message = f"JobSubmission with id={job_submission_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    job_submission = JobSubmissionResponse.from_orm(job_submission_data)
    logger.debug(f"Job-submission data: {job_submission}")

    return job_submission


@router.get(
    "/job-submissions",
    description="Endpoint to list job_submissions",
    responses=ok_response(JobSubmissionResponse),
)
async def job_submission_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(
        None,
        description="If supplied, do not limit job_submissions to only the current user",
    ),
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
    from_job_script_id: Optional[int] = Query(
        None,
        description="Filter job-submissions by the job-script-id they were created from.",
    ),
    sort_ascending: bool = Query(True),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_VIEW)),
):
    """
    List job_submissions for the authenticated user.
    """
    logger.debug("Fetching job submissions")

    logger.debug("Building query")
    query = select(job_submissions_table.c, job_scripts_table.c.job_script_name)
    if submit_status:
        query = query.where(job_submissions_table.c.status == submit_status)

    if not all:
        query = query.where(
            job_submissions_table.c.job_submission_owner_email == secure_session.identity_payload.email
        )

    if from_job_script_id is not None:
        query = query.where(job_submissions_table.c.job_script_id == from_job_script_id)
    if slurm_job_ids is not None and slurm_job_ids != "":
        try:
            job_ids = [int(i) for i in slurm_job_ids.split(",")]
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid slurm_job_ids param. Must be a comma-separated list of integers",
            )
        query = query.where(job_submissions_table.c.slurm_job_id.in_(job_ids))
    if search is not None:
        query = query.where(search_clause(search, searchable_fields))
    if sort_field is not None:
        query = query.order_by(sort_clause(sort_field, sortable_fields, sort_ascending))
    else:
        query = query.order_by(job_submissions_table.c.id.asc())

    full_query = query.join(
        job_scripts_table,
        job_scripts_table.columns.id == job_submissions_table.columns.job_script_id,
        isouter=True,
    )

    logger.trace(f"Query built as: {render_sql(secure_session.session, full_query)}")

    logger.debug("Awaiting query and response package")
    response = await package_response(secure_session.session, JobSubmissionResponse, full_query, pagination)

    logger.debug(f"Response built as: {response}")
    return response


@router.delete(
    "/job-submissions/{job_submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
)
async def job_submission_delete(
    job_submission_id: int = Query(..., description="id of the job submission to delete"),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_EDIT)),
):
    """
    Delete job_submission given its id.
    """
    logger.debug(f"Deleting {job_submission_id=}")

    job_submission = await _fetch_job_submission_by_id(secure_session, job_submission_id)
    check_owner(
        job_submission.job_submission_owner_email,
        secure_session.identity_payload.email,
        job_submission_id,
        "job_submission",
    )

    delete_query = job_submissions_table.delete().where(job_submissions_table.c.id == job_submission_id)
    logger.trace(f"delete_query = {render_sql(secure_session.session, delete_query)}")
    await secure_session.session.execute(delete_query)


@router.put(
    "/job-submissions/{job_submission_id}",
    status_code=status.HTTP_200_OK,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionResponse,
)
async def job_submission_update(
    job_submission_id: int,
    job_submission: JobSubmissionUpdateRequest,
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_EDIT)),
):
    """
    Update a job_submission given its id.
    """
    logger.debug(f"Updating {job_submission_id=}")

    old_job_submission = await _fetch_job_submission_by_id(secure_session, job_submission_id)
    check_owner(
        old_job_submission.job_submission_owner_email,
        secure_session.identity_payload.email,
        job_submission_id,
        "job_submission",
    )

    update_dict = job_submission.dict(exclude_unset=True)
    exec_dir = update_dict.pop("execution_directory", None)
    if exec_dir is not None:
        update_dict.update(execution_directory=str(exec_dir))

    update_query = (
        job_submissions_table.update()
        .where(job_submissions_table.c.id == job_submission_id)
        .values(update_dict)
        .returning(job_submissions_table)
    )
    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")
    try:
        raw_result = await secure_session.session.execute(update_query)
    except INTEGRITY_CHECK_EXCEPTIONS as e:
        logger.error(f"Reverting database transaction: {str(e)}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    job_submission_data = raw_result.one_or_none()
    if not job_submission_data:
        message = f"JobSubmission with id={job_submission_id} not found."
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return job_submission_data


# The "agent" routes are used for agents to fetch pending job submissions and update their statuses
@router.get(
    "/job-submissions/agent/pending",
    description="Endpoint to list pending job_submissions for the requesting client",
    response_model=List[PendingJobSubmission],
)
async def job_submissions_agent_pending(
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_VIEW)),
):
    """
    Get a list of pending job submissions for the cluster-agent.
    """
    logger.debug("Agent is requesting a list of pending job submissions")

    if secure_session.identity_payload.client_id is None:
        message = "Access token does not contain a `client_id`. Cannot fetch pending submissions"
        logger.warning(message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    logger.info(
        f"Fetching newly created job_submissions for client_id: {secure_session.identity_payload.client_id}"
    )

    query = (
        select(
            job_submissions_table.c.id,
            job_submissions_table.c.job_submission_name,
            job_submissions_table.c.job_submission_owner_email,
            job_submissions_table.c.execution_directory,
            job_submissions_table.c.execution_parameters,
            job_submissions_table.c.job_script_id,
            job_scripts_table.c.job_script_name,
            applications_table.c.application_name,
        )
        .where(job_submissions_table.c.status == JobSubmissionStatus.CREATED)
        .where(job_submissions_table.c.client_id == secure_session.identity_payload.client_id)
        .join(
            job_scripts_table,
            job_scripts_table.columns.id == job_submissions_table.columns.job_script_id,
            isouter=True,
        )
        .join(
            applications_table,
            applications_table.columns.id == job_scripts_table.columns.application_id,
            isouter=True,
        )
    )

    logger.trace(f"query = {render_sql(secure_session.session, query)}")
    raw_result = await secure_session.session.execute(query)
    rows = raw_result.fetchall()

    response = []
    missing_ids = set()

    for row in rows:
        jobscript_id = row.job_script_id
        try:
            job_script_files = JobScriptFiles.get_from_s3(jobscript_id)
        except (KeyError, ValueError) as e:
            logger.error(f"Error getting files for {jobscript_id=}: {str(e)}")
            missing_ids.add(jobscript_id)
        else:
            response.append(PendingJobSubmission(**row._mapping, job_script_files=job_script_files))

    if missing_ids:
        message = f"JobScript file(s) not found, the missing ids are: {', '.join(map(str, missing_ids))}"
        logger.error(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message,
        )

    return response


@router.put(
    "/job-submissions/agent/{job_submission_id}",
    status_code=200,
    description="Endpoint for an agent to update the status of a job_submission",
    response_model=JobSubmissionResponse,
)
async def job_submission_agent_update(
    job_submission_id: int,
    new_status: str = Body(..., embed=True),
    slurm_job_id: Optional[int] = Body(None, embed=True),
    report_message: Optional[str] = Body(None, embed=True),
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_EDIT)),
):
    """
    Update a job_submission with a new status.

    Make a put request to this endpoint with the new status to update a job_submission.
    """
    logger.debug(f"Agent is requesting to update {job_submission_id=}")

    if secure_session.identity_payload.client_id is None:
        logger.error("Access token does not contain a client_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token does not contain a `client_id`. Cannot update job_submission",
        )

    logger.info(
        f"Setting status to: {new_status} "
        f"for job_submission: {job_submission_id} "
        f"on client_id: {secure_session.identity_payload.client_id}"
    )

    update_values: Dict[str, Any] = dict(status=new_status)
    if slurm_job_id is not None:
        update_values.update(slurm_job_id=slurm_job_id)

    if report_message:
        update_values.update(report_message=report_message)

    update_query = (
        job_submissions_table.update()
        .where(job_submissions_table.c.id == job_submission_id)
        .where(job_submissions_table.c.client_id == secure_session.identity_payload.client_id)
        .values(**update_values)
        .returning(job_submissions_table)
    )
    logger.trace(f"update_query = {render_sql(secure_session.session, update_query)}")

    raw_result = await secure_session.session.execute(update_query)
    job_submission_data = raw_result.one_or_none()

    if job_submission_data is None:
        message = (
            f"JobSubmission with id={job_submission_id} "
            f"and client_id={secure_session.identity_payload.client_id} not found."
        )
        logger.warning(message)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(message),
        )

    if report_message and new_status == JobSubmissionStatus.REJECTED:
        notify_submission_rejected(
            job_submission_id, report_message, job_submission_data.job_submission_owner_email
        )

    return job_submission_data


@router.get(
    "/job-submissions/agent/active",
    description="Endpoint to list active job_submissions for the requesting client",
    response_model=List[ActiveJobSubmission],
)
async def job_submissions_agent_active(
    secure_session: SecureSession = Depends(secure_session(Permissions.JOB_SUBMISSIONS_VIEW)),
):
    """
    Get a list of active job submissions for the cluster-agent.
    """
    logger.debug("Agent is requesting a list of active job submissions")

    if secure_session.identity_payload.client_id is None:
        logger.error("Access token does not contain a client_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access token does not contain a `client_id`. Cannot fetch pending submissions",
        )

    logger.info(f"Fetching active job_submissions for client_id: {secure_session.identity_payload.client_id}")

    query = (
        job_submissions_table.select()
        .where(job_submissions_table.c.status == JobSubmissionStatus.SUBMITTED)
        .where(job_submissions_table.c.client_id == secure_session.identity_payload.client_id)
    )
    logger.trace(f"query = {render_sql(secure_session.session, query)}")

    raw_result = await secure_session.session.execute(query)
    return raw_result.fetchall()


def include_router(app):
    """
    Include the router for this module in the app.
    """
    app.include_router(router)
