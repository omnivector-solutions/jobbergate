"""
Router for the JobSubmission resource.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from jobbergateapi2.apps.auth.authentication import get_current_user
from jobbergateapi2.apps.job_scripts.models import job_scripts_table
from jobbergateapi2.apps.job_submissions.models import job_submissions_table
from jobbergateapi2.apps.job_submissions.schemas import JobSubmission, JobSubmissionRequest
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.storage import database

router = APIRouter()


@router.post("/job-submissions/", status_code=201, description="Endpoint for job_submission creation")
async def job_submission_create(
    job_submission: JobSubmissionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new job submission.

    Make a post request to this endpoint with the required values to create a new job submission.
    """
    query = job_scripts_table.select().where(
        (job_scripts_table.c.id == (job_submission.job_script_id))
        & (job_scripts_table.c.job_script_owner_id == (current_user.id))
    )
    raw_job_script = await database.fetch_one(query)

    if not raw_job_script:
        raise HTTPException(
            status_code=404,
            detail=(f"JobScript id={job_submission.job_script_id} not found for user={current_user.id}"),
        )

    job_submission = JobSubmission(job_submission_owner_id=current_user.id, **job_submission.dict())

    async with database.transaction():
        try:
            query = job_submissions_table.insert()
            values = job_submission.dict()
            job_submission_created_id = await database.execute(query=query, values=values)
            job_submission.id = job_submission_created_id

        except INTEGRITY_CHECK_EXCEPTIONS as e:
            raise HTTPException(status_code=422, detail=str(e))
    return job_submission


@router.get(
    "/job-submissions/{job_submission_id}",
    description="Endpoint to get a job_submission",
    response_model=JobSubmission,
)
async def job_submission_get(
    job_submission_id: int = Query(...), current_user: User = Depends(get_current_user)
):
    """
    Return the job_submission given it's id.
    """
    query = job_submissions_table.select().where(
        (job_submissions_table.c.id == job_submission_id)
        & (job_submissions_table.c.job_submission_owner_id == current_user.id)
    )
    raw_job_submission = await database.fetch_one(query)

    if not raw_job_submission:
        raise HTTPException(
            status_code=404,
            detail=f"JobSubmission with id={job_submission_id} not found for user={current_user.id}",
        )
    job_submission = JobSubmission.parse_obj(raw_job_submission)
    return job_submission


@router.get(
    "/job-submissions/", description="Endpoint to list job_submissions", response_model=List[JobSubmission]
)
async def job_submission_list(
    all: Optional[bool] = Query(None), current_user: User = Depends(get_current_user)
):
    """
    List job_submissions for the authenticated user.
    """
    if all:
        query = job_submissions_table.select()
    else:
        query = job_submissions_table.select().where(
            job_submissions_table.c.job_submission_owner_id == current_user.id
        )
    job_submissions = await database.fetch_all(query)
    return job_submissions


def include_router(app):
    app.include_router(router)
