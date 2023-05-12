"""
Router dependencies job_script_templates resource.

Note:
    The dependencies can be reused multiple times, since FastAPI caches the results.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from jobbergate_api.apps.dependecies import db_session, s3_bucket
from jobbergate_api.apps.job_scripts.service import JobScriptFilesService, JobScriptService


async def job_script_service(session: AsyncSession = Depends(db_session)) -> JobScriptService:
    """
    Dependency to get the job_script service.

    Returns:
        JobScriptService: The job_script service.
    """
    return JobScriptService(session=session)


async def job_script_files_service(
    session: AsyncSession = Depends(db_session),
    bucket=Depends(s3_bucket),
) -> JobScriptFilesService:
    """Dependency to get the job_script_files service."""
    return JobScriptFilesService(session, bucket)
