"""
Router dependencies job_submission_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session
from jobbergate_api.apps.job_submissions.models import JobSubmission
from jobbergate_api.apps.services import TableService


def job_submission_service(session: AsyncSession = Depends(db_session)) -> TableService:
    """Dependency to get the job_submission service."""
    return TableService(db_session=session, base_table=JobSubmission)
