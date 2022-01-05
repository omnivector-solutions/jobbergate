"""
Router for the JobSubmission resource.
"""
from typing import Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from jobbergate_api.apps.job_scripts.models import job_scripts_table
from jobbergate_api.apps.job_submissions.models import job_submissions_table
from jobbergate_api.apps.job_submissions.schemas import (
    JobSubmissionCreateRequest,
    JobSubmissionResponse,
    JobSubmissionUpdateRequest,
)
from jobbergate_api.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergate_api.pagination import Pagination, Response, package_response
from jobbergate_api.security import ArmadaClaims, guard
from jobbergate_api.storage import database

router = APIRouter()


@router.post("/job-submissions/", status_code=201, description="Endpoint for job_submission creation")
async def job_submission_create(
    job_submission: JobSubmissionCreateRequest,
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-submissions:create")),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    job_submission.job_submission_owner_email = armada_claims.user_email

    select_query = job_scripts_table.select().where(job_scripts_table.c.id == job_submission.job_script_id)
    raw_job_script = await database.fetch_one(select_query)

    if not raw_job_script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"JobScript id={job_submission.job_script_id} not found."),
        )

    async with database.transaction():
        try:
            insert_query = job_submissions_table.insert()
            inserted_id = await database.execute(query=insert_query, values=job_submission.dict(),)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

        # Now fetch the newly inserted row. This is necessary to reflect defaults and db modified columns
        query = job_submissions_table.select().where(job_submissions_table.c.id == inserted_id)
        raw_job_submission = await database.fetch_one(query)
        response_job_submission = JobSubmissionResponse.parse_obj(raw_job_submission)

    return response_job_submission


@router.get(
    "/job-submissions/{job_submission_id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmissionResponse,
    dependencies=[Depends(guard.lockdown("jobbergate:job-submissions:read"))],
)
async def job_submission_get(job_submission_id: int = Query(...)):
    """
    Return the job_submission given it's id.
    """
    query = job_submissions_table.select().where(job_submissions_table.c.id == job_submission_id)
    raw_job_submission = await database.fetch_one(query)

    if not raw_job_submission:
        raise HTTPException(
            status_code=404, detail=f"JobSubmission with id={job_submission_id} not found.",
        )
    job_submission = JobSubmissionResponse.parse_obj(raw_job_submission)
    return job_submission


@router.get(
    "/job-submissions/",
    description="Endpoint to list job_submissions",
    response_model=Response[JobSubmissionResponse],
)
async def job_submission_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(None),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-submissions:read")),
):
    """
    List job_submissions for the authenticated user.
    """
    armada_claims = ArmadaClaims.from_token_payload(token_payload)
    query = job_submissions_table.select()
    if not all:
        query = query.where(job_submissions_table.c.job_submission_owner_email == armada_claims.user_email)
    return await package_response(JobSubmissionResponse, query, pagination)


@router.delete(
    "/job-submissions/{job_submission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Endpoint to delete job submission",
    dependencies=[Depends(guard.lockdown("jobbergate:job-submissions:delete"))],
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
    dependencies=[Depends(guard.lockdown("jobbergate:job-submissions:update"))],
)
async def job_script_update(job_submission_id: int, job_submission: JobSubmissionUpdateRequest):
    """
    Update a job_submission given its id.
    """
    update_query = (
        job_submissions_table.update()
        .where(job_submissions_table.c.id == job_submission_id)
        .values(job_submission.dict(exclude_unset=True))
    )
    async with database.transaction():
        try:
            result = await database.execute(update_query)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JobSubmission with id={job_submission_id} not found.",
            )

        select_query = job_submissions_table.select().where(job_submissions_table.c.id == job_submission_id)
        raw_job_submission = await database.fetch_one(select_query)
        response_job_submission = JobSubmissionResponse.parse_obj(raw_job_submission)

    return response_job_submission


def include_router(app):
    app.include_router(router)
