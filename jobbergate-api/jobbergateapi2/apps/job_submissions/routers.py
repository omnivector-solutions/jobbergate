"""
Router for the JobSubmission resource.
"""
from datetime import datetime
from typing import List, Optional

from armasec import TokenPayload
from fastapi import APIRouter, Depends, Form, HTTPException, Query, status

from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_submissions.models import job_submissions_table
from jobbergateapi2.apps.job_submissions.schemas import JobSubmission, JobSubmissionRequest
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.pagination import Pagination, package_response, Response
from jobbergateapi2.security import guard
from jobbergateapi2.storage import database

router = APIRouter()


@router.post("/job-submissions/", status_code=201, description="Endpoint for job_submission creation")
async def job_submission_create(
    job_submission: JobSubmissionRequest,
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-submissions:create")),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    select_query = job_scripts_table.select().where(job_scripts_table.c.id == job_submission.job_script_id)
    raw_job_script = await database.fetch_one(select_query)

    if not raw_job_script:
        raise HTTPException(
            status_code=404, detail=(f"JobScript id={job_submission.job_script_id} not found."),
        )

    async with database.transaction():
        try:
            insert_query = job_submissions_table.insert()
            values = {"job_submission_owner_id": token_payload.sub, **job_submission.dict()}
            job_submission_created_id = await database.execute(query=insert_query, values=values)

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    return JobSubmission(
        id=job_submission_created_id, job_submission_owner_id=token_payload.sub, **job_submission.dict()
    )


@router.get(
    "/job-submissions/{job_submission_id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmission,
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
    job_submission = JobSubmission.parse_obj(raw_job_submission)
    return job_submission


@router.get(
    "/job-submissions/", description="Endpoint to list job_submissions", response_model=Response[JobSubmission]
)
async def job_submission_list(
    pagination: Pagination = Depends(),
    all: Optional[bool] = Query(None),
    token_payload: TokenPayload = Depends(guard.lockdown("jobbergate:job-submissions:read")),
):
    """
    List job_submissions for the authenticated user.
    """
    query = job_submissions_table.select()
    if not all:
        query = query.where(job_submissions_table.c.job_submission_owner_id == token_payload.sub)
    return await package_response(JobSubmission, query, pagination)


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
    response_model=JobSubmission,
    dependencies=[Depends(guard.lockdown("jobbergate:job-submissions:update"))],
)
async def job_script_update(
    job_submission_id: int = Query(...),
    job_submission_name: Optional[str] = Form(None),
    job_submission_description: Optional[str] = Form(None),
):
    """
    Update a job_submission given its id.
    """
    query = job_submissions_table.select().where(job_submissions_table.c.id == job_submission_id)
    raw_job_submission = await database.fetch_one(query)

    if not raw_job_submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"JobSubmission with id={job_submission_id} not found.",
        )
    job_submission_data = JobSubmission.parse_obj(raw_job_submission)

    if job_submission_name is not None:
        job_submission_data.job_submission_name = job_submission_name
    if job_submission_description is not None:
        job_submission_data.job_submission_description = job_submission_description

    job_submission_data.updated_at = datetime.utcnow()

    values = {
        "job_submission_name": job_submission_data.job_submission_name,
        "job_submission_description": job_submission_data.job_submission_description,
        "updated_at": job_submission_data.updated_at,
    }
    validated_values = {key: value for key, value in values.items() if value is not None}

    q_update = (
        job_submissions_table.update()
        .where(job_submissions_table.c.id == job_submission_id)
        .values(validated_values)
    )
    async with database.transaction():
        try:
            await database.execute(q_update)
        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    query = job_submissions_table.select(job_submissions_table.c.id == job_submission_id)
    return JobSubmission.parse_obj(await database.fetch_one(query))


def include_router(app):
    app.include_router(router)
