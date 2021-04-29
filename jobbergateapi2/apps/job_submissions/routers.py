from fastapi import APIRouter, Depends, HTTPException

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
            detail=f"JobScript with id={job_submission.job_script_id} not found for user={current_user.id}",
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


def include_router(app):
    app.include_router(router)
