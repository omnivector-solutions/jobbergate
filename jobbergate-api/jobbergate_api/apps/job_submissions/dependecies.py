"""
Router dependencies job_submission_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session
from jobbergate_api.apps.job_submissions.service import JobSubmissionService


async def job_submission_service(session: AsyncSession = Depends(db_session)) -> JobSubmissionService:
    """
    Dependency to get the job_submission service.

    Returns:
        JobSubmissionService: The job_submission service.
    """
    return JobSubmissionService(session=session)
