"""
Router for the JobSubmission resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.models import (
    job_submissions_table,
    searchable_fields,
    sortable_fields,
)
from jobbergate_api.apps.job_submissions.schemas import (
    JobSubmissionCreateRequest,
    JobSubmissionResponse,
    JobSubmissionUpdateRequest,
)
from jobbergate_api.apps.permissions import Permissions
from jobbergate_api.pagination import Pagination, ok_response, package_response
from jobbergate_api.security import IdentityClaims, guard
from jobbergate_api.storage import INTEGRITY_CHECK_EXCEPTIONS, database, search_clause, sort_clause

router = APIRouter()


@router.post(
    "/job-submissions",
    status_code=201,
    description="Endpoint for job_submission creation",
    response_model=JobSubmissionResponse,
)
async def job_submission_create(
    job_submission: JobSubmissionCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT)),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    job_submission.job_submission_owner_email = identity_claims.user_email

    select_query = job_scripts_table.select().where(job_scripts_table.c.id == job_submission.job_script_id)
    raw_job_script = await database.fetch_one(select_query)

    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"JobScript id={job_submission.job_script_id} not found."),
        )

    async with database.transaction():
        try:
            insert_query = job_submissions_table.insert().returning(job_submissions_table)
            job_submission_data = await database.fetch_one(query=insert_query, values=job_submission.dict())

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return job_submission_data


@router.get(
    "/job-submissions/{job_submission_id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW))],
)
async def job_submission_get(job_submission_id: int = Query(...)):
    """
    Return the job_submission given it's id.
    """
    query = job_submissions_table.select().where(job_submissions_table.c.id == job_submission_id)
    job_submission_data = await database.fetch_one(query)

    if not job_submission_data:
        raise HTTPException(status_code=404, detail=f"JobSubmission with id={job_submission_id} not found.")
    return job_submission_data


@router.get(
    "/job-submissions",
    description="Endpoint to list job_submissions",
    responses=ok_response(JobSubmissionResponse),
)
async def job_submission_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(
        None, description="If supplied, do not limit job_submissions to only the current user",
    ),
    slurm_job_ids: Optional[str] = Query(
        None, description="Comma-separated list of slurm-job-ids to match active job_submissions",
    ),
    search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_ascending: bool = Query(True),
    token_payload: TokenPayload = Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_VIEW)),
):
    """
    List job_submissions for the authenticated user.
    """
    identity_claims = IdentityClaims.from_token_payload(token_payload)
    query = job_submissions_table.select()

    if not all:
        query = query.where(job_submissions_table.c.job_submission_owner_email == identity_claims.user_email)

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

    return await package_response(JobSubmissionResponse, query, pagination)


@router.delete(
    "/job-submissions/{job_submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT))],
)
async def job_submission_delete(
    job_submission_id: int = Query(..., description="id of the job submission to delete"),
):
    """
    Delete job_submission given its id.
    """
    where_stmt = job_submissions_table.c.id == job_submission_id

    get_query = job_submissions_table.select().where(where_stmt)
    raw_job_submission = await database.fetch_one(get_query)
    if not raw_job_submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobSubmission with id={job_submission_id} not found",
        )

    delete_query = job_submissions_table.delete().where(where_stmt)
    await database.execute(delete_query)


@router.put(
    "/job-submissions/{job_submission_id}",
    status_code=status.HTTP_201_CREATED,
    description="Endpoint to update a job_submission given the id",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(guard.lockdown(Permissions.JOB_SUBMISSIONS_EDIT))],
)
async def job_script_update(job_submission_id: int, job_submission: JobSubmissionUpdateRequest):
    """
    Update a job_submission given its id.
    """
    update_query = (
        job_submissions_table.update()
        .where(job_submissions_table.c.id == job_submission_id)
        .values(job_submission.dict(exclude_unset=True))
        .returning(job_submissions_table)
    )
    async with database.transaction():
        try:
            job_submission_data = await database.fetch_one(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        if not job_submission_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JobSubmission with id={job_submission_id} not found.",
            )

    return job_submission_data


def include_router(app):
    app.include_router(router)
